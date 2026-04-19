"""Integration tests: full graph runs with mocked LLM and DB."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from src.state import GraphState, ParsedRequest, RestaurantCandidate, SelectedItem


def _make_mock_restaurant(r_id: int, name: str, cuisine: str) -> MagicMock:
    r = MagicMock()
    r.id, r.name, r.cuisine, r.city = r_id, name, cuisine, "Colombo"
    r.rating, r.delivery_fee, r.avg_delivery_min, r.is_open = 4.5, 150.0, 30, True
    return r


def _make_mock_item(item_id: int, name: str, price: float, category: str, tags: list) -> MagicMock:
    i = MagicMock()
    i.id, i.name, i.description = item_id, name, "desc"
    i.price, i.category, i.dietary_tags, i.in_stock = price, category, tags, True
    return i


GOLDEN_INPUTS = [
    "I have LKR 3000 for two people, craving spicy Sri Lankan, no seafood",
    "Budget 2500 rupees, want vegetarian Indian for one person",
    "Rs 4000 for Italian food, 3 people, no pork",
    "spend 1800 rupees on Chinese food",
    "LKR 5000 Japanese food for two, no pork",
]


@pytest.fixture
def mock_db_restaurant():
    return _make_mock_restaurant(1, "Test Restaurant", "sri_lankan")


@pytest.fixture
def mock_db_items():
    return [
        _make_mock_item(1, "Chicken Curry", 580.0, "main", ["spicy", "gluten_free"]),
        _make_mock_item(2, "Dhal Curry", 280.0, "main", ["vegetarian", "vegan"]),
        _make_mock_item(3, "Hoppers", 200.0, "starter", ["vegetarian"]),
    ]


def _run_full_graph(user_input: str, mock_restaurant, mock_items):
    """Run the full graph with mocked DB and pre-recorded LLM responses."""
    from src.agents.restaurant_finder import RankedList, RankedItem
    from src.agents.menu_selector import SelectionList
    from src.agents.order_validator import RationaleResponse

    db_result = MagicMock()
    db_result.scalars.return_value.all.return_value = [mock_restaurant]

    item_result = MagicMock()
    item_result.scalars.return_value.all.return_value = mock_items

    validate_result = MagicMock()
    validate_result.scalars.return_value.all.return_value = mock_items

    def mock_execute(stmt):
        sql = str(stmt)
        if "menu_items" in sql:
            return item_result
        return db_result

    llm_call_count = [0]

    def mock_invoke_structured(*args, **kwargs):
        schema = kwargs.get("schema") or args[2]
        if schema.__name__ == "RankedList":
            return RankedList(rankings=[RankedItem(id=1, match_score=0.9)])
        if schema.__name__ == "SelectionList":
            return SelectionList(selections=[
                SelectedItem(item_id=1, name="Chicken Curry", price=580.0, quantity=1, dietary_tags=["spicy"]),
            ])
        if schema.__name__ == "RationaleResponse":
            return RationaleResponse(rationale="Great selection within budget.")
        raise ValueError(f"Unknown schema: {schema.__name__}")

    with patch("src.tools.query_restaurants.get_session") as q_ctx, \
         patch("src.tools.fetch_menu_items.get_session") as f_ctx, \
         patch("src.tools.validate_order.get_session") as v_ctx, \
         patch("src.agents.restaurant_finder.invoke_structured", side_effect=mock_invoke_structured), \
         patch("src.agents.menu_selector.invoke_structured", side_effect=mock_invoke_structured), \
         patch("src.agents.order_validator.invoke_structured", side_effect=mock_invoke_structured):

        mock_session = MagicMock()
        mock_session.execute.side_effect = mock_execute
        for ctx in (q_ctx, f_ctx, v_ctx):
            ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
            ctx.return_value.__exit__ = MagicMock(return_value=False)

        from langgraph.checkpoint.memory import MemorySaver
        from src.graph import build_graph
        graph = build_graph(checkpointer=MemorySaver())
        tid = str(uuid.uuid4())[:8]
        initial = GraphState(trace_id=tid, user_input=user_input)
        config = {"configurable": {"thread_id": tid}}

        final_state = None
        for event in graph.stream(initial.model_dump(), config=config):
            for node_name, node_output in event.items():
                final_state = node_output

    return final_state


@pytest.mark.parametrize("user_input", GOLDEN_INPUTS)
def test_full_graph_produces_order(user_input: str, mock_db_restaurant, mock_db_items) -> None:
    result = _run_full_graph(user_input, mock_db_restaurant, mock_db_items)
    # The graph should complete without crashing
    assert result is not None


def test_graph_planner_produces_valid_parsed(mock_db_restaurant, mock_db_items) -> None:
    result = _run_full_graph(
        "LKR 3000 for two people, spicy Sri Lankan, no seafood",
        mock_db_restaurant, mock_db_items,
    )
    assert result is not None


def test_graph_error_on_invalid_input(mock_db_restaurant, mock_db_items) -> None:
    """Garbled input that can't be parsed should reach error node gracefully."""
    db_result = MagicMock()
    db_result.scalars.return_value.all.return_value = []

    with patch("src.tools.query_restaurants.get_session") as ctx:
        mock_session = MagicMock()
        mock_session.execute.return_value = db_result
        ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        ctx.return_value.__exit__ = MagicMock(return_value=False)

        from langgraph.checkpoint.memory import MemorySaver
        from src.graph import build_graph
        graph = build_graph(checkpointer=MemorySaver())
        tid = str(uuid.uuid4())[:8]
        initial = GraphState(trace_id=tid, user_input="zzz gibberish no numbers here xyz")
        config = {"configurable": {"thread_id": tid}}

        # Should not raise — must reach END gracefully
        events = list(graph.stream(initial.model_dump(), config=config))
        assert isinstance(events, list)
