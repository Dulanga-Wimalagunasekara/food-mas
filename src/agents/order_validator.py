from __future__ import annotations

import time

from pydantic import BaseModel

from src.llm import get_llm, invoke_structured
from src.logging_setup import TraceWriter, hash_state, node_logger
from src.state import AgentError, GraphState, OrderSummary
from src.tools.validate_order import ValidateOrderInput, validate_order

SYSTEM_PROMPT = """You are a friendly food ordering assistant writing a short order confirmation.
Given a validated order summary, write ONE sentence explaining why this selection is a great match for the user.
Focus only on qualitative aspects: cuisine fit, restaurant quality, dietary match, spice level, variety.
Do NOT mention any prices, totals, fees, or numbers — those are shown separately in the UI.

Output a JSON object with a single key "rationale" containing that single sentence.
Example: {"rationale": "We chose Laksala Kitchen for its top-rated spicy Sri Lankan menu that perfectly matches your taste and dietary preferences."}"""


class RationaleResponse(BaseModel):
    rationale: str


def run_order_validator(state: GraphState) -> dict:
    log = node_logger(state.trace_id, "order_validator", "order_validator_node")
    trace = TraceWriter(state.trace_id)
    t0 = time.monotonic()

    is_multi = bool(state.sub_requests and state.chosen_restaurant_ids)
    has_single = state.chosen_restaurant_id is not None

    if state.parsed is None or not state.selected_items or (not has_single and not is_multi):
        return {"order": None, "errors": [AgentError(
            agent="order_validator", kind="validation",
            message="Incomplete state for validation", recoverable=False,
        )]}

    parsed = state.parsed

    if is_multi:
        restaurant_id = 0
        restaurant_name = "Multiple Restaurants"
        delivery_fee = sum(
            next((c.delivery_fee for c in state.candidates if c.id == rid), 150.0)
            for rid in state.chosen_restaurant_ids
        )
        log.info("node.enter", input_hash=hash_state({
            "restaurant_ids": state.chosen_restaurant_ids,
            "item_count": len(state.selected_items),
        }))
    else:
        restaurant_id = state.chosen_restaurant_id  # type: ignore[assignment]
        restaurant_name = next(
            (c.name for c in state.candidates if c.id == restaurant_id),
            f"Restaurant #{restaurant_id}",
        )
        delivery_fee = next(
            (c.delivery_fee for c in state.candidates if c.id == restaurant_id),
            150.0,
        )
        log.info("node.enter", input_hash=hash_state({
            "restaurant_id": restaurant_id,
            "item_count": len(state.selected_items),
        }))

    tool_result = validate_order(ValidateOrderInput(
        restaurant_id=restaurant_id,
        restaurant_name=restaurant_name,
        items=state.selected_items,
        delivery_fee=delivery_fee,
        budget_lkr=parsed.budget_lkr,
        dietary_exclude=parsed.dietary_exclude,
    ))

    if not tool_result.is_ok():
        err = tool_result.unwrap()
        error = AgentError(
            agent="order_validator", kind="tool_failure",
            message=err.message, recoverable=True,
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
        log.error("node.exit", status="tool_error", latency_ms=latency_ms)
        trace.write({"node": "order_validator", "status": "tool_error", "latency_ms": latency_ms})
        return {"order": None, "errors": [error]}

    validation = tool_result.unwrap()
    order: OrderSummary = validation.order

    # Generate rationale via LLM (only job for the LLM in this agent)
    order_summary_text = (
        f"Restaurant: {restaurant_name}. "
        f"Items: {[f'{i.name} x{i.quantity} @ LKR {i.price}' for i in order.items]}. "
        f"Subtotal: {order.subtotal} LKR, Delivery: {order.delivery_fee} LKR, "
        f"Tax: {order.tax} LKR, Total: {order.total} LKR. "
        f"Budget: {parsed.budget_lkr} LKR. Within budget: {order.within_budget}. "
        f"Stock issues: {validation.stock_failures}. "
        f"Dietary issues: {validation.dietary_violations}."
    )

    budget_status = "within" if order.within_budget else "over"
    if parsed.budget_lkr < 99999:
        cost_line = (
            f"Your order totals LKR {order.total:,.0f} ({budget_status} your "
            f"LKR {parsed.budget_lkr:,.0f} budget), including delivery and tax."
        )
    else:
        cost_line = f"Your order totals LKR {order.total:,.0f}, including delivery and tax."

    try:
        llm_response = invoke_structured(
            llm=get_llm(temperature=0.1),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": order_summary_text},
            ],
            schema=RationaleResponse,
            trace_id=state.trace_id,
            agent="order_validator",
            max_retries=2,
        )
        rationale = f"{llm_response.rationale} {cost_line}"
    except ValueError:
        rationale = cost_line

    final_order = OrderSummary(**{**order.model_dump(), "rationale": rationale})

    latency_ms = int((time.monotonic() - t0) * 1000)
    log.info("node.exit", status="ok", within_budget=final_order.within_budget,
             total=final_order.total, latency_ms=latency_ms,
             output_hash=hash_state(final_order.model_dump()))
    trace.write({"node": "order_validator", "status": "ok",
                 "order": final_order.model_dump(), "latency_ms": latency_ms,
                 "stock_failures": validation.stock_failures,
                 "dietary_violations": validation.dietary_violations})
    return {"order": final_order}
