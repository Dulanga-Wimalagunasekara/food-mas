from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel

from src.llm import get_llm, invoke_structured
from src.logging_setup import TraceWriter, hash_state, node_logger
from src.state import AgentError, GraphState, ParsedRequest, RestaurantCandidate
from src.tools.query_restaurants import QueryRestaurantsInput, query_restaurants

SYSTEM_PROMPT = """You are a restaurant ranking assistant. Given a list of restaurants and a user's parsed request, rank them by fit and assign a match_score between 0.0 and 1.0.

Rules:
- Higher score = better match for the user's preferences.
- Consider: cuisine match, rating, delivery time, delivery fee relative to budget.
- Do not invent restaurants. Only rank the ones provided.
- Output a JSON array. Each element must have: id (int), match_score (float 0-1).
- No prose, no markdown. JSON array only.

Example output:
[{"id": 3, "match_score": 0.95}, {"id": 7, "match_score": 0.72}]"""


class RankedItem(BaseModel):
    id: int
    match_score: float


class RankedList(BaseModel):
    rankings: list[RankedItem]


def _rank_candidates(
    raw: list[RestaurantCandidate],
    parsed: ParsedRequest,
    trace_id: str,
) -> list[RestaurantCandidate]:
    candidates_payload = [
        {
            "id": c.id, "name": c.name, "cuisine": c.cuisine,
            "rating": c.rating, "delivery_fee": c.delivery_fee,
            "avg_delivery_min": c.avg_delivery_min,
        }
        for c in raw
    ]
    user_context = (
        f"Budget: {parsed.budget_lkr} LKR, party of {parsed.party_size}. "
        f"Wants: {parsed.cuisines}. "
        f"Requires: {parsed.dietary_require}. "
        f"Excludes: {parsed.dietary_exclude}. "
        f"Spice: {parsed.spice_preference}."
    )
    try:
        llm_response = invoke_structured(
            llm=get_llm(temperature=0.1),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": (
                    f"User request: {user_context}\n\nRestaurants: {candidates_payload}\n\n"
                    "Return a JSON object with key 'rankings' containing the ranked list."
                )},
            ],
            schema=RankedList,
            trace_id=trace_id,
            agent="restaurant_finder",
            max_retries=2,
        )
        score_map: dict[int, float] = {r.id: max(0.0, min(1.0, r.match_score)) for r in llm_response.rankings}
    except ValueError:
        max_rating = max((c.rating for c in raw), default=5.0)
        score_map = {c.id: c.rating / max_rating for c in raw}

    scored = [
        RestaurantCandidate(**{**c.model_dump(), "match_score": score_map.get(c.id, 0.5)})
        for c in raw
    ]
    scored.sort(key=lambda c: c.match_score, reverse=True)
    return scored


def run_restaurant_finder(state: GraphState) -> dict:
    log = node_logger(state.trace_id, "restaurant_finder", "restaurant_finder_node")
    trace = TraceWriter(state.trace_id)
    t0 = time.monotonic()

    if state.parsed is None:
        return {"candidates": [], "errors": [AgentError(
            agent="restaurant_finder", kind="validation",
            message="No parsed request available", recoverable=False,
        )]}

    # Multi-restaurant mode
    if state.sub_requests:
        all_candidates: list[RestaurantCandidate] = []
        chosen_ids: list[int] = []
        seen_ids: set[int] = set()

        for sub_req in state.sub_requests:
            tool_result = query_restaurants(QueryRestaurantsInput(
                cuisines=sub_req.cuisines,
                city=sub_req.city,
                min_rating=3.5,
                limit=5,
            ))
            if not tool_result.is_ok():
                continue
            raw = tool_result.unwrap().restaurants
            if not raw:
                continue
            scored = _rank_candidates(raw, sub_req, state.trace_id)
            if scored:
                chosen_ids.append(scored[0].id)
                for c in scored:
                    if c.id not in seen_ids:
                        all_candidates.append(c)
                        seen_ids.add(c.id)

        latency_ms = int((time.monotonic() - t0) * 1000)
        if not chosen_ids:
            log.info("node.exit", status="no_results", latency_ms=latency_ms)
            trace.write({"node": "restaurant_finder", "status": "no_results", "latency_ms": latency_ms})
            return {"candidates": []}

        log.info("node.exit", status="ok_multi", count=len(chosen_ids), latency_ms=latency_ms,
                 output_hash=hash_state([c.model_dump() for c in all_candidates]))
        trace.write({"node": "restaurant_finder", "status": "ok_multi",
                     "chosen_ids": chosen_ids, "latency_ms": latency_ms})
        return {"candidates": all_candidates, "chosen_restaurant_ids": chosen_ids}

    #Single-restaurant mode
    log.info("node.enter", input_hash=hash_state(state.parsed.model_dump()))
    parsed: ParsedRequest = state.parsed

    tool_result = query_restaurants(QueryRestaurantsInput(
        cuisines=parsed.cuisines,
        city=parsed.city,
        min_rating=3.5,
        limit=10,
    ))

    if not tool_result.is_ok():
        err = tool_result.unwrap()
        error = AgentError(
            agent="restaurant_finder", kind="tool_failure",
            message=err.message, recoverable=True,
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
        log.error("node.exit", status="tool_error", latency_ms=latency_ms)
        trace.write({"node": "restaurant_finder", "status": "tool_error", "latency_ms": latency_ms})
        return {"candidates": [], "errors": [error]}

    raw_candidates: list[RestaurantCandidate] = tool_result.unwrap().restaurants

    if not raw_candidates:
        latency_ms = int((time.monotonic() - t0) * 1000)
        log.info("node.exit", status="no_results", latency_ms=latency_ms)
        trace.write({"node": "restaurant_finder", "status": "no_results", "latency_ms": latency_ms})
        return {"candidates": []}

    scored = _rank_candidates(raw_candidates, parsed, state.trace_id)

    latency_ms = int((time.monotonic() - t0) * 1000)
    log.info("node.exit", status="ok", count=len(scored), latency_ms=latency_ms,
             output_hash=hash_state([c.model_dump() for c in scored]))
    trace.write({"node": "restaurant_finder", "status": "ok",
                 "candidates": [c.model_dump() for c in scored], "latency_ms": latency_ms})
    return {"candidates": scored, "chosen_restaurant_id": scored[0].id if scored else None}
