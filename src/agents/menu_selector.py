from __future__ import annotations

import time

from pydantic import BaseModel

from src.llm import get_llm, invoke_structured
from src.logging_setup import TraceWriter, hash_state, node_logger
from src.state import AgentError, GraphState, ParsedRequest, RestaurantCandidate, SelectedItem
from src.tools.fetch_menu_items import FetchMenuItemsInput, fetch_menu_items

SYSTEM_PROMPT = """You are a menu selection assistant. Select menu items from the provided list that:
1. Fit within the remaining budget (budget minus delivery fee).
2. Respect all dietary exclusions — do NOT select items with excluded tags.
3. Select only what the customer asked for. If a category filter is specified, honour it exactly.
4. Use the item's description to match flavour and texture cues from the user's request (e.g. "spicy and sour", "creamy", "grilled", "light"). Prefer items whose description aligns with those cues.
5. Maximise variety and satisfaction within budget.

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


def _select_items_for(
    restaurant_id: int,
    sub_req: ParsedRequest,
    candidates: list[RestaurantCandidate],
    trace_id: str,
    user_input: str = "",
) -> list[SelectedItem]:
    """Select menu items from a single restaurant for the given sub-request."""
    restaurant_name = next((c.name for c in candidates if c.id == restaurant_id), "")
    delivery_fee = next(
        (c.delivery_fee for c in candidates if c.id == restaurant_id), 150.0
    )
    spendable = sub_req.budget_lkr - delivery_fee

    tool_result = fetch_menu_items(FetchMenuItemsInput(
        restaurant_id=restaurant_id,
        dietary_exclude=sub_req.dietary_exclude,
        categories=sub_req.categories,
    ))

    if not tool_result.is_ok():
        return []

    available = tool_result.unwrap().items
    if not available:
        return []

    menu_payload = [
        {"item_id": i.id, "name": i.name, "description": i.description,
         "price": i.price, "category": i.category, "dietary_tags": i.dietary_tags}
        for i in available
    ]

    category_note = (
        f"Category filter (select ONLY these categories): {sub_req.categories}. "
        if sub_req.categories else ""
    )
    user_input_note = (
        f"User's original request (use for flavour/texture matching against descriptions): \"{user_input}\". "
        if user_input else ""
    )
    prompt_context = (
        f"Budget remaining after delivery: {spendable:.2f} LKR. "
        f"Party size: {sub_req.party_size}. "
        f"{category_note}"
        f"Dietary exclusions: {sub_req.dietary_exclude}. "
        f"Dietary requirements: {sub_req.dietary_require}. "
        f"Spice preference: {sub_req.spice_preference}. "
        f"{user_input_note}"
    )

    valid_ids = {i.id for i in available}
    price_map = {i.id: i.price for i in available}
    tag_map = {i.id: i.dietary_tags for i in available}
    exclude_set = set(sub_req.dietary_exclude)

    selected: list[SelectedItem] = []
    for _ in range(3):
        try:
            llm_response = invoke_structured(
                llm=get_llm(temperature=0.3),
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"{prompt_context}\n\nAvailable menu: {menu_payload}"},
                ],
                schema=SelectionList,
                trace_id=trace_id,
                agent="menu_selector",
                max_retries=2,
            )

            verified: list[SelectedItem] = []
            for sel in llm_response.selections:
                if sel.item_id not in valid_ids:
                    continue
                if exclude_set.intersection(tag_map[sel.item_id]):
                    continue
                verified.append(SelectedItem(
                    item_id=sel.item_id,
                    name=sel.name,
                    price=price_map[sel.item_id],
                    quantity=max(1, sel.quantity),
                    dietary_tags=tag_map[sel.item_id],
                    restaurant_name=restaurant_name,
                ))

            actual_total = sum(i.price * i.quantity for i in verified)
            if actual_total <= spendable and verified:
                selected = verified
                break
        except ValueError:
            pass

    if not selected:
        # Greedy fallback: cheapest item that fits
        candidates_sorted = sorted(available, key=lambda x: x.price)
        for item in candidates_sorted:
            if sum(s.price * s.quantity for s in selected) + item.price <= spendable:
                selected.append(SelectedItem(
                    item_id=item.id, name=item.name, price=item.price,
                    quantity=1, dietary_tags=item.dietary_tags,
                    restaurant_name=restaurant_name,
                ))
                break

    return selected


def run_menu_selector(state: GraphState) -> dict:
    log = node_logger(state.trace_id, "menu_selector", "menu_selector_node")
    trace = TraceWriter(state.trace_id)
    t0 = time.monotonic()

    if state.parsed is None:
        return {"selected_items": [], "errors": [AgentError(
            agent="menu_selector", kind="validation",
            message="Missing parsed request", recoverable=False,
        )]}

    #Multi-restaurant mode
    if state.sub_requests and state.chosen_restaurant_ids:
        all_items: list[SelectedItem] = []
        for sub_req, rest_id in zip(state.sub_requests, state.chosen_restaurant_ids):
            items = _select_items_for(rest_id, sub_req, state.candidates, state.trace_id, state.user_input)
            all_items.extend(items)

        latency_ms = int((time.monotonic() - t0) * 1000)
        log.info("node.exit", status="ok_multi", item_count=len(all_items), latency_ms=latency_ms,
                 output_hash=hash_state([s.model_dump() for s in all_items]))
        trace.write({"node": "menu_selector", "status": "ok_multi",
                     "selected_items": [s.model_dump() for s in all_items], "latency_ms": latency_ms})
        return {"selected_items": all_items}

    #Single-restaurant mode
    if state.chosen_restaurant_id is None:
        return {"selected_items": [], "errors": [AgentError(
            agent="menu_selector", kind="validation",
            message="Missing restaurant selection", recoverable=False,
        )]}

    log.info("node.enter", input_hash=hash_state({
        "restaurant_id": state.chosen_restaurant_id,
        "budget": state.parsed.budget_lkr,
    }))

    selected_items = _select_items_for(
        state.chosen_restaurant_id, state.parsed, state.candidates, state.trace_id, state.user_input
    )

    latency_ms = int((time.monotonic() - t0) * 1000)
    log.info("node.exit", status="ok", item_count=len(selected_items), latency_ms=latency_ms,
             output_hash=hash_state([s.model_dump() for s in selected_items]))
    trace.write({"node": "menu_selector", "status": "ok",
                 "selected_items": [s.model_dump() for s in selected_items], "latency_ms": latency_ms})
    return {"selected_items": selected_items}
