from __future__ import annotations

import re
import time

from src.llm import get_llm, invoke_structured
from src.logging_setup import TraceWriter, hash_state, node_logger
from src.state import AgentError, GraphState, ParsedRequest
from src.tools.parse_request import CATEGORY_MAP, CUISINE_MAP, ParseRequestInput, parse_request

SYSTEM_PROMPT = """You are a food-ordering request parser. Your only job is to convert one user message into a strict JSON object matching the ParsedRequest schema.

Rules:
- Currency is LKR. If user says "Rs 3000", "3000" or "3k rupees", budget_lkr=3000. If no budget is stated, use 99999.
- If party_size is not stated, default to 1.
- cuisines must be from: sri_lankan, indian, chinese, italian, american, japanese, thai. Map synonyms ("pasta" -> italian, "sushi" -> japanese, "burger" -> american).
- categories: menu categories the customer explicitly wants. Use only: main, starter, dessert, drink, side. Leave empty [] if no category is mentioned.
- dietary_exclude: anything the user says they don't want (e.g. "no seafood" -> ["seafood"]).
- dietary_require: dietary lifestyles user requires (e.g. "vegetarian", "vegan").
- spice_preference: "mild" | "medium" | "hot" | null.
- city: city name if stated, otherwise "Colombo".
- Never invent constraints the user did not state.
- Output valid JSON only. No prose, no markdown, no extra keys.

Schema:
{"budget_lkr": float, "party_size": int, "cuisines": [str], "categories": [str], "dietary_exclude": [str], "dietary_require": [str], "spice_preference": str|null, "city": str}

Example:
User: "I have 2500 rupees, want veggie Indian, no dairy"
Output: {"budget_lkr": 2500, "party_size": 1, "cuisines": ["indian"], "categories": [], "dietary_exclude": ["dairy"], "dietary_require": ["vegetarian"], "spice_preference": null, "city": "Colombo"}"""


def _detect_sub_requests(user_input: str, parsed: ParsedRequest) -> list[ParsedRequest]:
    """Detect multi-restaurant requests like 'main from Sri Lanka and dessert from Italy'.

    Looks for explicit 'category from cuisine' patterns. Returns a list of
    sub-ParsedRequests (one per pair) when 2+ distinct pairs are found.
    """
    text = user_input.lower()

    cat_terms = "|".join(re.escape(k) for k in sorted(CATEGORY_MAP.keys(), key=len, reverse=True))
    cuisine_terms = "|".join(re.escape(k) for k in sorted(CUISINE_MAP.keys(), key=len, reverse=True))
    # Allow 0-2 filler words between "from" and the cuisine keyword so that
    # "from sri lanka" matches even though "lanka" is the map key, not "sri lanka".
    pattern = rf"({cat_terms})\s+from\s+(?:\w+\s+){{0,2}}({cuisine_terms})"

    seen: set[tuple[str, str]] = set()
    pairs: list[tuple[str, str]] = []
    for m in re.finditer(pattern, text):
        category = CATEGORY_MAP[m.group(1)]
        cuisine = CUISINE_MAP[m.group(2)]
        key = (cuisine, category)
        if key not in seen:
            seen.add(key)
            pairs.append(key)

    if len(pairs) < 2:
        return []

    budget_each = parsed.budget_lkr / len(pairs)
    return [
        ParsedRequest(
            budget_lkr=budget_each,
            party_size=parsed.party_size,
            cuisines=[cuisine],
            categories=[category],
            dietary_exclude=parsed.dietary_exclude,
            dietary_require=parsed.dietary_require,
            spice_preference=parsed.spice_preference,
            city=parsed.city,
        )
        for cuisine, category in pairs
    ]


def run_planner(state: GraphState) -> dict:
    log = node_logger(state.trace_id, "planner", "planner_node")
    trace = TraceWriter(state.trace_id)
    t0 = time.monotonic()

    log.info("node.enter", input_hash=hash_state(state.user_input))

    # Primary: LLM — better at understanding natural language
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": state.user_input},
    ]
    if state.errors:
        last_err = state.errors[-1]
        messages.append({
            "role": "user",
            "content": f"Previous attempt failed: {last_err.message}. Try again carefully.",
        })
    try:
        parsed = invoke_structured(
            llm=get_llm(temperature=0.1),
            messages=messages,
            schema=ParsedRequest,
            trace_id=state.trace_id,
            agent="planner",
            max_retries=2,
        )
    except ValueError:
        # Fallback: deterministic regex tool — injection-safe, no LLM needed
        log.info("planner.llm_failed_using_regex_fallback")
        tool_result = parse_request(ParseRequestInput(
            raw_text=state.user_input,
            default_city="Colombo",
        ))
        if tool_result.is_ok():
            parsed = ParsedRequest(**tool_result.unwrap().model_dump())
        else:
            latency_ms = int((time.monotonic() - t0) * 1000)
            error = AgentError(
                agent="planner",
                kind="parse_failure",
                message="Both LLM and regex parser failed to extract a valid request.",
                recoverable=True,
            )
            log.error("node.exit", status="error", latency_ms=latency_ms)
            trace.write({"node": "planner", "status": "error", "error": error.model_dump(), "latency_ms": latency_ms})
            retries = dict(state.retries)
            retries["planner"] = retries.get("planner", 0) + 1
            return {"parsed": None, "errors": [error], "retries": retries}

    sub_requests = _detect_sub_requests(state.user_input, parsed)

    latency_ms = int((time.monotonic() - t0) * 1000)
    log.info("node.exit", status="ok", latency_ms=latency_ms,
             sub_requests=len(sub_requests), output_hash=hash_state(parsed.model_dump()))
    trace.write({"node": "planner", "status": "ok", "parsed": parsed.model_dump(),
                 "sub_requests": len(sub_requests), "latency_ms": latency_ms})
    return {"parsed": parsed, "sub_requests": sub_requests}
