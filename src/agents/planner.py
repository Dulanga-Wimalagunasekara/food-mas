from __future__ import annotations

import time

from src.llm import get_llm, invoke_structured
from src.logging_setup import TraceWriter, hash_state, node_logger
from src.state import AgentError, GraphState, ParsedRequest
from src.tools.parse_request import ParseRequestInput, parse_request

SYSTEM_PROMPT = """You are a food-ordering request parser. Your only job is to convert one user message into a strict JSON object matching the ParsedRequest schema.

Rules:
- Currency is LKR. If user says "Rs 3000" or "3k rupees", budget_lkr=3000.
- If party_size is not stated, default to 1.
- cuisines must be from: sri_lankan, indian, chinese, italian, american, japanese, thai. Map synonyms ("pasta" -> italian, "sushi" -> japanese, "burger" -> american).
- dietary_exclude: anything the user says they don't want (e.g. "no seafood" -> ["seafood"]).
- dietary_require: dietary lifestyles user requires (e.g. "vegetarian", "vegan").
- spice_preference: "mild" | "medium" | "hot" | null.
- city: city name if stated, otherwise "Colombo".
- Never invent constraints the user did not state.
- Output valid JSON only. No prose, no markdown, no extra keys.

Schema:
{"budget_lkr": float, "party_size": int, "cuisines": [str], "dietary_exclude": [str], "dietary_require": [str], "spice_preference": str|null, "city": str}

Example:
User: "I have 2500 rupees, want veggie Indian, no dairy"
Output: {"budget_lkr": 2500, "party_size": 1, "cuisines": ["indian"], "dietary_exclude": ["dairy"], "dietary_require": ["vegetarian"], "spice_preference": null, "city": "Colombo"}"""


def run_planner(state: GraphState) -> dict:
    log = node_logger(state.trace_id, "planner", "planner_node")
    trace = TraceWriter(state.trace_id)
    t0 = time.monotonic()

    log.info("node.enter", input_hash=hash_state(state.user_input))

    # First try the deterministic rule-based tool
    tool_result = parse_request(ParseRequestInput(
        raw_text=state.user_input,
        default_city="Colombo",
    ))

    if tool_result.is_ok():
        out = tool_result.unwrap()
        parsed = ParsedRequest(
            budget_lkr=out.budget_lkr,
            party_size=out.party_size,
            cuisines=out.cuisines,
            dietary_exclude=out.dietary_exclude,
            dietary_require=out.dietary_require,
            spice_preference=out.spice_preference,
            city=out.city,
        )
    else:
        # Fall back to LLM
        log.info("planner.tool_failed_using_llm", reason=tool_result.unwrap().message)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": state.user_input},
        ]
        # Append prior error context if retrying
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
        except ValueError as exc:
            latency_ms = int((time.monotonic() - t0) * 1000)
            error = AgentError(
                agent="planner",
                kind="llm_refusal",
                message=str(exc),
                recoverable=True,
            )
            log.error("node.exit", status="error", latency_ms=latency_ms)
            trace.write({"node": "planner", "status": "error", "error": error.model_dump(), "latency_ms": latency_ms})
            retries = dict(state.retries)
            retries["planner"] = retries.get("planner", 0) + 1
            return {"parsed": None, "errors": [error], "retries": retries}

    latency_ms = int((time.monotonic() - t0) * 1000)
    log.info("node.exit", status="ok", latency_ms=latency_ms, output_hash=hash_state(parsed.model_dump()))
    trace.write({"node": "planner", "status": "ok", "parsed": parsed.model_dump(), "latency_ms": latency_ms})
    return {"parsed": parsed}
