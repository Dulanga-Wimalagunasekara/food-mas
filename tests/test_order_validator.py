"""Unit tests for the Order Validator agent."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.agents.order_validator import run_order_validator
from src.state import GraphState, ParsedRequest, RestaurantCandidate, SelectedItem


def _make_state(items: list[SelectedItem] | None = None, budget: float = 3000.0) -> GraphState:
    if items is None:
        items = [
            SelectedItem(item_id=1, name="Chicken Curry", price=580.0, quantity=1, dietary_tags=["spicy"]),
            SelectedItem(item_id=3, name="Hoppers", price=200.0, quantity=1, dietary_tags=["vegetarian"]),
        ]
    return GraphState(
        trace_id="test-validator",
        user_input="test",
        parsed=ParsedRequest(
            budget_lkr=budget, party_size=1, cuisines=["sri_lankan"],
            dietary_exclude=[], dietary_require=[], spice_preference=None, city="Colombo",
        ),
        candidates=[RestaurantCandidate(
            id=1, name="Laksala Kitchen", cuisine="sri_lankan",
            rating=4.5, delivery_fee=150.0, avg_delivery_min=30, match_score=0.9,
        )],
        chosen_restaurant_id=1,
        selected_items=items,
    )


def _mock_db_rows(item_ids: list[int], in_stock: bool = True) -> list[MagicMock]:
    rows = []
    specs = {
        1: ("Chicken Curry", 580.0, ["spicy"]),
        3: ("Hoppers", 200.0, ["vegetarian"]),
        99: ("Out of Stock Item", 300.0, []),
    }
    for iid in item_ids:
        name, price, tags = specs.get(iid, (f"Item{iid}", 300.0, []))
        r = MagicMock()
        r.id = iid
        r.name = name
        r.price = price
        r.dietary_tags = tags
        r.in_stock = in_stock
        rows.append(r)
    return rows


def test_validator_correct_total_arithmetic() -> None:
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = _mock_db_rows([1, 3])

    with patch("src.tools.validate_order.get_session") as ctx, \
         patch("src.agents.order_validator.invoke_structured") as mock_llm:

        mock_session = MagicMock()
        mock_session.execute.return_value = mock_result
        ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        ctx.return_value.__exit__ = MagicMock(return_value=False)

        from src.agents.order_validator import RationaleResponse
        mock_llm.return_value = RationaleResponse(rationale="Great choice!")

        state = _make_state()
        result = run_order_validator(state)

    order = result["order"]
    assert order is not None
    subtotal = 580.0 + 200.0
    tax = round(subtotal * 0.10, 2)
    total = round(subtotal + 150.0 + tax, 2)
    assert abs(order.subtotal - subtotal) < 0.01
    assert abs(order.tax - tax) < 0.01
    assert abs(order.total - total) < 0.01


def test_validator_within_budget_flag() -> None:
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = _mock_db_rows([1, 3])

    with patch("src.tools.validate_order.get_session") as ctx, \
         patch("src.agents.order_validator.invoke_structured") as mock_llm:

        mock_session = MagicMock()
        mock_session.execute.return_value = mock_result
        ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        ctx.return_value.__exit__ = MagicMock(return_value=False)

        from src.agents.order_validator import RationaleResponse
        mock_llm.return_value = RationaleResponse(rationale="Good value!")

        # Budget of 500 is too small: 580+200+150+78(tax) = 1008
        state = _make_state(budget=500.0)
        result = run_order_validator(state)

    assert result["order"] is not None
    assert result["order"].within_budget is False


def test_validator_detects_out_of_stock() -> None:
    items = [SelectedItem(item_id=99, name="Out of Stock Item", price=300.0, quantity=1, dietary_tags=[])]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = _mock_db_rows([99], in_stock=False)

    with patch("src.tools.validate_order.get_session") as ctx, \
         patch("src.agents.order_validator.invoke_structured") as mock_llm:

        mock_session = MagicMock()
        mock_session.execute.return_value = mock_result
        ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        ctx.return_value.__exit__ = MagicMock(return_value=False)

        from src.agents.order_validator import RationaleResponse
        mock_llm.return_value = RationaleResponse(rationale="Noted.")

        state = _make_state(items=items)
        result = run_order_validator(state)

    assert result["order"].within_budget is False


def test_validator_rationale_fallback_on_llm_failure() -> None:
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = _mock_db_rows([1, 3])

    with patch("src.tools.validate_order.get_session") as ctx, \
         patch("src.agents.order_validator.invoke_structured", side_effect=ValueError("LLM down")):

        mock_session = MagicMock()
        mock_session.execute.return_value = mock_result
        ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        ctx.return_value.__exit__ = MagicMock(return_value=False)

        state = _make_state()
        result = run_order_validator(state)

    assert result["order"] is not None
    assert len(result["order"].rationale) > 0
