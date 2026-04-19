"""Unit tests for the Restaurant Finder agent."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.agents.restaurant_finder import run_restaurant_finder
from src.state import GraphState, ParsedRequest, RestaurantCandidate


def _make_state(parsed: ParsedRequest | None = None) -> GraphState:
    return GraphState(
        trace_id="test-finder",
        user_input="test",
        parsed=parsed,
    )


def _make_parsed(**kwargs) -> ParsedRequest:
    defaults = dict(
        budget_lkr=3000.0, party_size=2, cuisines=["sri_lankan"],
        dietary_exclude=[], dietary_require=[], spice_preference="hot", city="Colombo",
    )
    defaults.update(kwargs)
    return ParsedRequest(**defaults)


def _mock_candidates() -> list[MagicMock]:
    rows = []
    for i, (name, cuisine, rating) in enumerate([
        ("Laksala Kitchen", "sri_lankan", 4.5),
        ("Curry Leaf Bistro", "sri_lankan", 4.2),
    ]):
        r = MagicMock()
        r.id = i + 1
        r.name = name
        r.cuisine = cuisine
        r.city = "Colombo"
        r.rating = rating
        r.delivery_fee = 150.0
        r.avg_delivery_min = 30
        r.is_open = True
        rows.append(r)
    return rows


def test_finder_returns_candidates_when_db_has_results() -> None:
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = _mock_candidates()

    with patch("src.tools.query_restaurants.get_session") as ctx, \
         patch("src.agents.restaurant_finder.invoke_structured") as mock_llm:

        mock_session = MagicMock()
        mock_session.execute.return_value = mock_result
        ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        ctx.return_value.__exit__ = MagicMock(return_value=False)

        from src.agents.restaurant_finder import RankedList, RankedItem
        mock_llm.return_value = RankedList(rankings=[
            RankedItem(id=1, match_score=0.95),
            RankedItem(id=2, match_score=0.72),
        ])

        state = _make_state(_make_parsed())
        result = run_restaurant_finder(state)

    assert len(result["candidates"]) == 2
    assert result["candidates"][0].match_score >= result["candidates"][1].match_score


def test_finder_returns_empty_on_no_db_results() -> None:
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []

    with patch("src.tools.query_restaurants.get_session") as ctx:
        mock_session = MagicMock()
        mock_session.execute.return_value = mock_result
        ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        ctx.return_value.__exit__ = MagicMock(return_value=False)

        state = _make_state(_make_parsed())
        result = run_restaurant_finder(state)

    assert result["candidates"] == []


def test_finder_errors_on_no_parsed_state() -> None:
    state = _make_state(parsed=None)
    result = run_restaurant_finder(state)
    assert result["candidates"] == []
    assert len(result["errors"]) > 0


def test_finder_falls_back_to_rating_score_on_llm_failure() -> None:
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = _mock_candidates()

    with patch("src.tools.query_restaurants.get_session") as ctx, \
         patch("src.agents.restaurant_finder.invoke_structured", side_effect=ValueError("LLM failed")):

        mock_session = MagicMock()
        mock_session.execute.return_value = mock_result
        ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        ctx.return_value.__exit__ = MagicMock(return_value=False)

        state = _make_state(_make_parsed())
        result = run_restaurant_finder(state)

    assert len(result["candidates"]) == 2
    for c in result["candidates"]:
        assert 0.0 <= c.match_score <= 1.0
