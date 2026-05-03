from __future__ import annotations

import re
import time
from typing import Optional

from pydantic import BaseModel

from src.llm import get_llm, invoke_structured
from src.logging_setup import TraceWriter, hash_state, node_logger
from src.state import AgentError, GraphState, ParsedRequest
from src.tools.parse_request import CATEGORY_MAP, CUISINE_MAP, ParseRequestInput, parse_request

SYSTEM_PROMPT = """You are a food-ordering request parser. Convert one user message into a strict JSON object.

Rules:
- Currency is LKR. "Rs 3000", "3k rupees" → budget_lkr=3000. No budget stated → 99999.
- party_size: default 1 if not mentioned.
- cuisines: use ONLY: sri_lankan, indian, chinese, italian, american, japanese, thai. Map synonyms ("pasta"→italian, "sushi"→japanese, "burger"→american, "curry"→indian).
- categories: explicit requests only. Use ONLY: main, starter, dessert, drink, side. Leave [] if none mentioned.
- dietary_exclude: things user doesn't want (e.g. "no seafood" → ["seafood"]).
- dietary_require: dietary lifestyles required (e.g. "vegetarian", "halal").
- spice_preference: "mild" | "medium" | "hot" | null.
- city: stated city, otherwise "Colombo".
- sub_requests: populate ONLY when the user clearly wants items from 2+ different cuisine types in one order.
  Each entry has its own cuisines and categories for that part of the order.
  Leave as [] for normal single-restaurant requests.
- Output valid JSON only. No prose, no markdown, no extra keys.

Schema:
{"budget_lkr": float, "party_size": int, "cuisines": [str], "categories": [str],
 "dietary_exclude": [str], "dietary_require": [str], "spice_preference": str|null, "city": str,
 "sub_requests": [{"cuisines": [str], "categories": [str]}]}

Examples:
User: "spicy Sri Lankan for 2, LKR 3000"
Output: {"budget_lkr": 3000, "party_size": 2, "cuisines": ["sri_lankan"], "categories": [], "dietary_exclude": [], "dietary_require": [], "spice_preference": "hot", "city": "Colombo", "sub_requests": []}

User: "something spicy from Sri Lanka and a dessert from Italy"
Output: {"budget_lkr": 99999, "party_size": 1, "cuisines": ["sri_lankan", "italian"], "categories": [], "dietary_exclude": [], "dietary_require": [], "spice_preference": "hot", "city": "Colombo", "sub_requests": [{"cuisines": ["sri_lankan"], "categories": []}, {"cuisines": ["italian"], "categories": ["dessert"]}]}

User: "main dish from Sri Lanka and drinks from Japan"
Output: {"budget_lkr": 99999, "party_size": 1, "cuisines": ["sri_lankan", "japanese"], "categories": [], "dietary_exclude": [], "dietary_require": [], "spice_preference": null, "city": "Colombo", "sub_requests": [{"cuisines": ["sri_lankan"], "categories": ["main"]}, {"cuisines": ["japanese"], "categories": ["drink"]}]}

User: "a main from Sri Lanka and a dessert from Japan"
Output: {"budget_lkr": 99999, "party_size": 1, "cuisines": ["sri_lankan", "japanese"], "categories": [], "dietary_exclude": [], "dietary_require": [], "spice_preference": null, "city": "Colombo", "sub_requests": [{"cuisines": ["sri_lankan"], "categories": ["main"]}, {"cuisines": ["japanese"], "categories": ["dessert"]}]}"""


class SubRequestSpec(BaseModel):
    cuisines: list[str]
    categories: list[str] = []


class PlannerOutput(BaseModel):
    budget_lkr: float
    party_size: int
    cuisines: list[str]
    categories: list[str] = []
    dietary_exclude: list[str]
    dietary_require: list[str]
    spice_preference: Optional[str] = None
    city: str
    sub_requests: list[SubRequestSpec] = []


def _build_sub_requests(
    specs: list[SubRequestSpec],
    parsed: ParsedRequest,
) -> list[ParsedRequest]:
    """Convert LLM-produced SubRequestSpec list into full ParsedRequest objects."""
    budget_each = parsed.budget_lkr / len(specs)
    return [
        ParsedRequest(
            budget_lkr=budget_each,
            party_size=parsed.party_size,
            cuisines=spec.cuisines,
            categories=spec.categories,
            dietary_exclude=parsed.dietary_exclude,
            dietary_require=parsed.dietary_require,
            spice_preference=parsed.spice_preference,
            city=parsed.city,
        )
        for spec in specs
    ]


def _detect_sub_requests_regex(user_input: str, parsed: ParsedRequest) -> list[ParsedRequest]:
    """Regex fallback for multi-restaurant detection when LLM doesn't produce sub_requests."""
    text = user_input.lower()
    cat_terms = "|".join(re.escape(k) for k in sorted(CATEGORY_MAP.keys(), key=len, reverse=True))
    cuisine_terms = "|".join(re.escape(k) for k in sorted(CUISINE_MAP.keys(), key=len, reverse=True))
    pattern = rf"(?:({cat_terms})\s+)?from\s+(?:\w+\s+){{0,2}}({cuisine_terms})"

    seen: set[tuple[str, str | None]] = set()
    pairs: list[tuple[str, str | None]] = []
    for m in re.finditer(pattern, text):
        category = CATEGORY_MAP[m.group(1)] if m.group(1) else None
        cuisine = CUISINE_MAP[m.group(2)]
        key = (cuisine, category)
        if key not in seen:
            seen.add(key)
            pairs.append((cuisine, category))

    if len(pairs) < 2:
        return []

    budget_each = parsed.budget_lkr / len(pairs)
    return [
        ParsedRequest(
            budget_lkr=budget_each,
            party_size=parsed.party_size,
            cuisines=[cuisine],
            categories=[category] if category else [],
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

    # Primary: LLM — understands natural language and detects multi-restaurant intent
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
        llm_out = invoke_structured(
            llm=get_llm(temperature=0.1),
            messages=messages,
            schema=PlannerOutput,
            trace_id=state.trace_id,
            agent="planner",
            max_retries=2,
        )
        parsed = ParsedRequest(**{k: v for k, v in llm_out.model_dump().items() if k != "sub_requests"})
        if len(llm_out.sub_requests) >= 2:
            sub_requests = _build_sub_requests(llm_out.sub_requests, parsed)
        else:
            # LLM missed multi-restaurant intent — try regex as a second pass
            sub_requests = _detect_sub_requests_regex(state.user_input, parsed)
    except ValueError:
        # Fallback: deterministic regex tool — injection-safe, no LLM needed
        log.info("planner.llm_failed_using_regex_fallback")
        tool_result = parse_request(ParseRequestInput(
            raw_text=state.user_input,
            default_city="Colombo",
        ))
        if tool_result.is_ok():
            parsed = ParsedRequest(**tool_result.unwrap().model_dump())
            sub_requests = _detect_sub_requests_regex(state.user_input, parsed)
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

    latency_ms = int((time.monotonic() - t0) * 1000)
    log.info("node.exit", status="ok", latency_ms=latency_ms,
             sub_requests=len(sub_requests), output_hash=hash_state(parsed.model_dump()))
    trace.write({"node": "planner", "status": "ok", "parsed": parsed.model_dump(),
                 "sub_requests": len(sub_requests), "latency_ms": latency_ms})
    return {"parsed": parsed, "sub_requests": sub_requests}
