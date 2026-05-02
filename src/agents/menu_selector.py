from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel

from src.llm import get_llm, invoke_structured
from src.logging_setup import TraceWriter, hash_state, node_logger
from src.state import AgentError, GraphState, SelectedItem
from src.tools.fetch_menu_items import FetchMenuItemsInput, fetch_menu_items

SYSTEM_PROMPT = """You are a menu selection assistant. Select menu items from the provided list that:
1. Fit within the remaining budget (budget minus delivery fee).
2. Respect all dietary exclusions — do NOT select items with excluded tags.
3. Select only what the customer asked for. If a category filter is specified, honour it exactly.
4. Maximise variety and satisfaction within budget.

Output a JSON object with key "selections" containing an array of selected items.
Each item must have: item_id (int), name (str), price (float), quantity (int), dietary_tags (list of str).
Use only item_ids from the provided list. Do not invent items or IDs.

Example output:
{"selections": [
  {"item_id": 12, "name": "Butter Chicken", "price": 720.0, "quantity": 2, "dietary_tags": []},
  {"item_id": 15, "name": "Garlic Naan", "price": 180.0, "quantity": 2, "dietary_tags": ["vegetarian"]}
]}"""


class SelectionList(BaseModel):
    selections: list[SelectedItem]


def run_menu_selector(state: GraphState) -> dict:
    log = node_logger(state.trace_id, "menu_selector", "menu_selector_node")
    trace = TraceWriter(state.trace_id)
    t0 = time.monotonic()

    if state.parsed is None or state.chosen_restaurant_id is None:
        return {"selected_items": [], "errors": [AgentError(
            agent="menu_selector", kind="validation",
            message="Missing parsed request or restaurant selection", recoverable=False,
        )]}

    log.info("node.enter", input_hash=hash_state({
        "restaurant_id": state.chosen_restaurant_id,
        "budget": state.parsed.budget_lkr,
    }))

    parsed = state.parsed
    restaurant_id = state.chosen_restaurant_id

    # Find delivery fee for chosen restaurant
    delivery_fee = next(
        (c.delivery_fee for c in state.candidates if c.id == restaurant_id),
        150.0,
    )
    spendable = parsed.budget_lkr - delivery_fee

    tool_result = fetch_menu_items(FetchMenuItemsInput(
        restaurant_id=restaurant_id,
        dietary_exclude=parsed.dietary_exclude,
        categories=parsed.categories,
    ))

    if not tool_result.is_ok():
        err = tool_result.unwrap()
        error = AgentError(
            agent="menu_selector", kind="tool_failure",
            message=err.message, recoverable=True,
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
        log.error("node.exit", status="tool_error", latency_ms=latency_ms)
        trace.write({"node": "menu_selector", "status": "tool_error", "latency_ms": latency_ms})
        return {"selected_items": [], "errors": [error]}

    available = tool_result.unwrap().items
    if not available:
        latency_ms = int((time.monotonic() - t0) * 1000)
        log.info("node.exit", status="no_items", latency_ms=latency_ms)
        trace.write({"node": "menu_selector", "status": "no_items", "latency_ms": latency_ms})
        return {"selected_items": []}

    menu_payload = [
        {"item_id": i.id, "name": i.name, "price": i.price, "category": i.category,
         "dietary_tags": i.dietary_tags}
        for i in available
    ]

    category_note = f"Category filter (select ONLY these categories): {parsed.categories}. " if parsed.categories else ""
    prompt_context = (
        f"Budget remaining after delivery: {spendable:.2f} LKR. "
        f"Party size: {parsed.party_size}. "
        f"{category_note}"
        f"Dietary exclusions: {parsed.dietary_exclude}. "
        f"Dietary requirements: {parsed.dietary_require}. "
        f"Spice preference: {parsed.spice_preference}."
    )

    selected_items: list[SelectedItem] = []
    for attempt in range(3):
        try:
            llm_response = invoke_structured(
                llm=get_llm(temperature=0.3),
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"{prompt_context}\n\nAvailable menu: {menu_payload}"},
                ],
                schema=SelectionList,
                trace_id=state.trace_id,
                agent="menu_selector",
                max_retries=2,
            )

            # Deterministic post-check: verify IDs exist and recalculate total
            valid_ids = {i.id for i in available}
            price_map = {i.id: i.price for i in available}
            tag_map = {i.id: i.dietary_tags for i in available}
            exclude_set = set(parsed.dietary_exclude)

            verified: list[SelectedItem] = []
            for sel in llm_response.selections:
                if sel.item_id not in valid_ids:
                    continue  # LLM hallucinated an ID — skip
                if exclude_set.intersection(tag_map[sel.item_id]):
                    continue  # dietary violation — skip
                # Use DB price, not LLM-reported price
                verified.append(SelectedItem(
                    item_id=sel.item_id,
                    name=sel.name,
                    price=price_map[sel.item_id],
                    quantity=max(1, sel.quantity),
                    dietary_tags=tag_map[sel.item_id],
                ))

            actual_total = sum(i.price * i.quantity for i in verified)
            if actual_total <= spendable and verified:
                selected_items = verified
                break

            # Budget exceeded or no valid items — retry with tighter instruction
        except ValueError:
            pass

    if not selected_items:
        # Greedy fallback: cheapest items that fit within budget
        candidates = sorted(available, key=lambda x: x.price)
        for item in candidates:
            if sum(s.price * s.quantity for s in selected_items) + item.price <= spendable:
                selected_items.append(SelectedItem(
                    item_id=item.id, name=item.name, price=item.price,
                    quantity=1, dietary_tags=item.dietary_tags,
                ))
                break

    latency_ms = int((time.monotonic() - t0) * 1000)
    log.info("node.exit", status="ok", item_count=len(selected_items), latency_ms=latency_ms,
             output_hash=hash_state([s.model_dump() for s in selected_items]))
    trace.write({"node": "menu_selector", "status": "ok",
                 "selected_items": [s.model_dump() for s in selected_items], "latency_ms": latency_ms})
    return {"selected_items": selected_items}
