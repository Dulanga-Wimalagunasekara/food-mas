"""Unit tests for the Planner agent."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.agents.planner import run_planner
from src.state import GraphState


def _make_state(user_input: str) -> GraphState:
    return GraphState(trace_id="test-planner", user_input=user_input)


@pytest.mark.parametrize("text,expected", [
    (
        "I have LKR 3000 for two people, craving spicy Sri Lankan, no seafood",
        {"budget_lkr": 3000.0, "party_size": 2, "cuisines": ["sri_lankan"],
         "dietary_exclude": ["seafood"], "spice_preference": "hot"},
    ),
    (
        "Budget 2500 rupees, want vegetarian Indian for one person",
        {"budget_lkr": 2500.0, "party_size": 1, "cuisines": ["indian"],
         "dietary_require": ["vegetarian"]},
    ),
    (
        "Rs 4000 for Italian food, 3 people, no pork",
        {"budget_lkr": 4000.0, "party_size": 3, "cuisines": ["italian"],
         "dietary_exclude": ["pork"]},
    ),
    (
        "spend 1800 rupees on Chinese food",
        {"budget_lkr": 1800.0, "cuisines": ["chinese"]},
    ),
    (
        "2000 LKR sushi for two",
        {"budget_lkr": 2000.0, "party_size": 2, "cuisines": ["japanese"]},
    ),
])
def test_planner_golden_inputs(text: str, expected: dict) -> None:
    state = _make_state(text)
    result = run_planner(state)

    assert result.get("parsed") is not None, f"Planner returned no parsed for: {text!r}"
    parsed = result["parsed"]

    for key, val in expected.items():
        actual = getattr(parsed, key)
        if isinstance(val, list):
            assert set(val).issubset(set(actual)), f"{key}: expected {val} in {actual}"
        else:
            assert actual == val, f"{key}: expected {val}, got {actual}"


def test_planner_sets_default_party_size() -> None:
    state = _make_state("LKR 2000 want Thai food")
    result = run_planner(state)
    assert result["parsed"].party_size == 1


def test_planner_rejects_oversized_input() -> None:
    state = _make_state("a" * 6000)
    result = run_planner(state)
    assert result.get("parsed") is None
    assert len(result.get("errors", [])) > 0


def test_planner_increments_retry_counter() -> None:
    state = _make_state("a" * 6000)
    result = run_planner(state)
    assert result.get("retries", {}).get("planner", 0) >= 1


def test_planner_no_invented_constraints() -> None:
    state = _make_state("LKR 3000 Italian food")
    result = run_planner(state)
    parsed = result["parsed"]
    assert parsed is not None
    assert parsed.dietary_exclude == []
    assert parsed.dietary_require == []
    assert parsed.spice_preference is None
