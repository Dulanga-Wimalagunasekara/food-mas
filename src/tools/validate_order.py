from __future__ import annotations

from pydantic import BaseModel
from sqlalchemy import select

from src.db.models import MenuItem
from src.db.session import get_session
from src.state import OrderSummary, SelectedItem
from src.tools.base import Err, Ok, Result, ToolError, tool_with_retry

TAX_RATE = 0.10


class ValidateOrderInput(BaseModel):
    restaurant_id: int
    restaurant_name: str
    items: list[SelectedItem]
    delivery_fee: float
    budget_lkr: float
    dietary_exclude: list[str]


class ValidateOrderOutput(BaseModel):
    order: OrderSummary
    stock_failures: list[str]     # item names that failed stock check
    dietary_violations: list[str] # item names that violate exclusions


@tool_with_retry(timeout_s=10, retries=2)
def validate_order(inp: ValidateOrderInput) -> Result[ValidateOrderOutput, ToolError]:
    """Re-validate order against live DB state: stock, totals, and dietary constraints.

    All arithmetic is deterministic Python — no LLM involvement. The LLM's
    only contribution (the rationale field) is filled with a placeholder here
    and replaced by the Order Validator agent after this tool returns.

    Args:
        inp: Selected items, restaurant metadata, delivery fee, budget, and
             dietary exclusions to enforce.

    Returns:
        Ok(ValidateOrderOutput) always (even for invalid orders — callers
        inspect stock_failures and within_budget on the OrderSummary), or
        Err(ToolError) on DB failure.

    Raises:
        Never raises — exceptions are caught and returned as Err.

    Example:
        >>> result = validate_order(ValidateOrderInput(
        ...     restaurant_id=1, restaurant_name="Test",
        ...     items=[SelectedItem(item_id=1, name="X", price=500, quantity=1, dietary_tags=[])],
        ...     delivery_fee=150.0, budget_lkr=1000.0, dietary_exclude=[]
        ... ))
        >>> result.is_ok()
        True
    """
    try:
        item_ids = [item.item_id for item in inp.items]

        with get_session() as session:
            rows = session.execute(
                select(MenuItem).where(MenuItem.id.in_(item_ids))
            ).scalars().all()

        db_by_id: dict[int, MenuItem] = {r.id: r for r in rows}

        stock_failures: list[str] = []
        dietary_violations: list[str] = []
        exclude_set = set(inp.dietary_exclude)

        for item in inp.items:
            db_row = db_by_id.get(item.item_id)
            if db_row is None or not db_row.in_stock:
                stock_failures.append(item.name)

            if db_row is not None:
                tags = db_row.dietary_tags if isinstance(db_row.dietary_tags, list) else []
                if exclude_set.intersection(tags):
                    dietary_violations.append(item.name)

        subtotal = sum(item.price * item.quantity for item in inp.items)
        tax = round(subtotal * TAX_RATE, 2)
        total = round(subtotal + inp.delivery_fee + tax, 2)
        within_budget = (
            total <= inp.budget_lkr
            and not stock_failures
            and not dietary_violations
        )

        order = OrderSummary(
            restaurant_id=inp.restaurant_id,
            restaurant_name=inp.restaurant_name,
            items=inp.items,
            subtotal=round(subtotal, 2),
            delivery_fee=inp.delivery_fee,
            tax=tax,
            total=total,
            within_budget=within_budget,
            rationale="",  # filled by Order Validator agent
        )

        return Ok(ValidateOrderOutput(
            order=order,
            stock_failures=stock_failures,
            dietary_violations=dietary_violations,
        ))

    except Exception as exc:
        return Err(ToolError(tool="validate_order", kind="db_error", message=str(exc)))
