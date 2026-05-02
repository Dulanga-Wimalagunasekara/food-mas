"""Unit tests for the Menu Selector agent."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.agents.menu_selector import run_menu_selector
from src.state import GraphState, ParsedRequest, RestaurantCandidate, SelectedItem


def _make_state(**kwargs) -> GraphState:
    defaults = dict(
        trace_id="test-selector",
        user_input="test",
        parsed=ParsedRequest(
            budget_lkr=3000.0, party_size=1, cuisines=["sri_lankan"], categories=[],
            dietary_exclude=[], dietary_require=[], spice_preference=None, city="Colombo",
        ),
        candidates=[RestaurantCandidate(
            id=1, name="Laksala Kitchen", cuisine="sri_lankan",
            rating=4.5, delivery_fee=150.0, avg_delivery_min=30, match_score=0.9,
        )],
        chosen_restaurant_id=1,
    )
    defaults.update(kwargs)
    return GraphState(**defaults)


def _mock_menu_rows() -> list[MagicMock]:
    items = [
        (1, "Chicken Curry", 580.0, "main", ["spicy", "gluten_free"]),
        (2, "Dhal Curry", 280.0, "main", ["vegetarian", "vegan"]),
        (3, "Hoppers", 200.0, "starter", ["vegetarian"]),
        (4, "Watalappan", 320.0, "dessert", ["vegetarian"]),
    ]
    rows = []
    for item_id, name, price, cat, tags in items:
        r = MagicMock()
        r.id = item_id
        r.name = name
        r.description = "desc"
        r.price = price
        r.category = cat
        r.dietary_tags = tags
        r.in_stock = True
        rows.append(r)
    return rows


def test_selector_returns_items_within_budget() -> None:
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = _mock_menu_rows()

    with patch("src.tools.fetch_menu_items.get_session") as ctx, \
         patch("src.agents.menu_selector.invoke_structured") as mock_llm:

        mock_session = MagicMock()
        mock_session.execute.return_value = mock_result
        ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        ctx.return_value.__exit__ = MagicMock(return_value=False)

        from src.agents.menu_selector import SelectionList
        mock_llm.return_value = SelectionList(selections=[
            SelectedItem(item_id=1, name="Chicken Curry", price=580.0, quantity=1, dietary_tags=["spicy"]),
            SelectedItem(item_id=3, name="Hoppers", price=200.0, quantity=1, dietary_tags=["vegetarian"]),
        ])

        state = _make_state()
        result = run_menu_selector(state)

    assert len(result["selected_items"]) >= 1
    total = sum(i.price * i.quantity for i in result["selected_items"])
    budget_after_delivery = 3000.0 - 150.0
    assert total <= budget_after_delivery


def test_selector_filters_excluded_dietary_tags() -> None:
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = _mock_menu_rows()

    with patch("src.tools.fetch_menu_items.get_session") as ctx, \
         patch("src.agents.menu_selector.invoke_structured") as mock_llm:

        mock_session = MagicMock()
        mock_session.execute.return_value = mock_result
        ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        ctx.return_value.__exit__ = MagicMock(return_value=False)

        from src.agents.menu_selector import SelectionList
        # LLM tries to sneak in a "spicy" item when user excluded "spicy"
        mock_llm.return_value = SelectionList(selections=[
            SelectedItem(item_id=1, name="Chicken Curry", price=580.0, quantity=1, dietary_tags=["spicy"]),
        ])

        state = _make_state(parsed=ParsedRequest(
            budget_lkr=3000.0, party_size=1, cuisines=["sri_lankan"], categories=[],
            dietary_exclude=["spicy"], dietary_require=[], spice_preference=None, city="Colombo",
        ))
        result = run_menu_selector(state)

    for item in result["selected_items"]:
        assert "spicy" not in item.dietary_tags


def test_selector_rejects_hallucinated_item_ids() -> None:
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = _mock_menu_rows()

    with patch("src.tools.fetch_menu_items.get_session") as ctx, \
         patch("src.agents.menu_selector.invoke_structured") as mock_llm:

        mock_session = MagicMock()
        mock_session.execute.return_value = mock_result
        ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        ctx.return_value.__exit__ = MagicMock(return_value=False)

        from src.agents.menu_selector import SelectionList
        mock_llm.return_value = SelectionList(selections=[
            SelectedItem(item_id=9999, name="Ghost Dish", price=100.0, quantity=1, dietary_tags=[]),
        ])

        state = _make_state()
        result = run_menu_selector(state)

    item_ids = [i.item_id for i in result["selected_items"]]
    assert 9999 not in item_ids


def test_selector_greedy_fallback_on_llm_failure() -> None:
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = _mock_menu_rows()

    with patch("src.tools.fetch_menu_items.get_session") as ctx, \
         patch("src.agents.menu_selector.invoke_structured", side_effect=ValueError("LLM down")):

        mock_session = MagicMock()
        mock_session.execute.return_value = mock_result
        ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        ctx.return_value.__exit__ = MagicMock(return_value=False)

        state = _make_state()
        result = run_menu_selector(state)

    # Greedy fallback should still return at least one item
    assert len(result["selected_items"]) >= 1
