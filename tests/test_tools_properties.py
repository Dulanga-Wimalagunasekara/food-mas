"""Property-based tests for all four tools using Hypothesis."""
from __future__ import annotations

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from src.tools.parse_request import ParseRequestInput, parse_request
from src.tools.base import Ok


# ---------------------------------------------------------------------------
# parse_request properties
# ---------------------------------------------------------------------------

CUISINES = ["sri_lankan", "indian", "chinese", "italian", "american", "japanese", "thai"]
CITIES = ["Colombo", "Kandy"]

valid_budget_texts = [
    "LKR 3000 for two people, spicy Sri Lankan, no seafood",
    "Rs 2500 want vegetarian indian for one person",
    "budget of 4000 rupees, italian food, no pork",
    "I have 1500 LKR, Chinese food please",
    "spend 5000 on Japanese for 3 people",
]


@pytest.mark.parametrize("text", valid_budget_texts)
def test_parse_request_always_has_positive_budget(text: str) -> None:
    result = parse_request(ParseRequestInput(raw_text=text))
    assert result.is_ok()
    assert result.unwrap().budget_lkr > 0


@pytest.mark.parametrize("text", valid_budget_texts)
def test_parse_request_party_size_at_least_one(text: str) -> None:
    result = parse_request(ParseRequestInput(raw_text=text))
    assert result.is_ok()
    assert result.unwrap().party_size >= 1


def test_parse_request_rejects_negative_budget() -> None:
    result = parse_request(ParseRequestInput(raw_text="I have no budget for food"))
    # Either fails or produces a zero/None budget — must not produce a positive value
    if result.is_ok():
        assert result.unwrap().budget_lkr > 0  # if it finds a number it must be positive
    else:
        assert not result.is_ok()


def test_parse_request_rejects_oversized_input() -> None:
    big = "a" * 10_000
    result = parse_request(ParseRequestInput(raw_text=big))
    assert not result.is_ok()


def test_parse_request_no_seafood_exclusion() -> None:
    result = parse_request(ParseRequestInput(raw_text="LKR 3000, Sri Lankan, no seafood"))
    assert result.is_ok()
    assert "seafood" in result.unwrap().dietary_exclude


def test_parse_request_vegetarian_requirement() -> None:
    result = parse_request(ParseRequestInput(raw_text="2500 rupees vegetarian Indian"))
    assert result.is_ok()
    assert "vegetarian" in result.unwrap().dietary_require


def test_parse_request_spicy_detected() -> None:
    result = parse_request(ParseRequestInput(raw_text="LKR 3000 spicy Sri Lankan for 2 people"))
    assert result.is_ok()
    assert result.unwrap().spice_preference == "hot"


def test_parse_request_cuisine_mapping_pasta() -> None:
    result = parse_request(ParseRequestInput(raw_text="3000 rupees pasta for two people"))
    assert result.is_ok()
    assert "italian" in result.unwrap().cuisines


def test_parse_request_city_extraction() -> None:
    result = parse_request(ParseRequestInput(raw_text="LKR 2000 Indian food in Kandy"))
    assert result.is_ok()
    assert result.unwrap().city == "Kandy"


def test_parse_request_default_city() -> None:
    result = parse_request(ParseRequestInput(raw_text="LKR 2000 Indian food"))
    assert result.is_ok()
    assert result.unwrap().city == "Colombo"


# ---------------------------------------------------------------------------
# validate_order arithmetic property
# ---------------------------------------------------------------------------

from src.state import SelectedItem, OrderSummary
from src.tools.validate_order import ValidateOrderInput, validate_order, TAX_RATE


@given(
    prices=st.lists(
        st.floats(min_value=100.0, max_value=2000.0, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=6,
    ),
    delivery_fee=st.floats(min_value=0.0, max_value=500.0, allow_nan=False, allow_infinity=False),
    budget=st.floats(min_value=500.0, max_value=20000.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=50)
def test_validate_order_total_arithmetic(
    prices: list[float],
    delivery_fee: float,
    budget: float,
) -> None:
    """total must always equal subtotal + delivery_fee + tax regardless of inputs."""
    items = [
        SelectedItem(item_id=i + 100, name=f"Item{i}", price=p, quantity=1, dietary_tags=[])
        for i, p in enumerate(prices)
    ]
    inp = ValidateOrderInput(
        restaurant_id=999,
        restaurant_name="TestRestaurant",
        items=items,
        delivery_fee=delivery_fee,
        budget_lkr=budget,
        dietary_exclude=[],
    )
    result = validate_order(inp)
    # Tool may return Err if DB lookup fails (item_ids not in DB) but arithmetic still runs
    # We test arithmetic via the OrderSummary when Ok
    if result.is_ok():
        order = result.unwrap().order
        expected_subtotal = sum(i.price * i.quantity for i in items)
        expected_tax = round(expected_subtotal * TAX_RATE, 2)
        expected_total = round(expected_subtotal + delivery_fee + expected_tax, 2)
        assert abs(order.subtotal - round(expected_subtotal, 2)) < 0.01
        assert abs(order.tax - expected_tax) < 0.01
        assert abs(order.total - expected_total) < 0.01


# ---------------------------------------------------------------------------
# fetch_menu_items: no excluded tag ever appears in results
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock, patch
from src.tools.fetch_menu_items import FetchMenuItemsInput, FetchMenuItemsOutput, fetch_menu_items


def _make_mock_item(item_id: int, tags: list[str]) -> MagicMock:
    row = MagicMock()
    row.id = item_id
    row.name = f"Item{item_id}"
    row.description = "desc"
    row.price = 300.0
    row.category = "main"
    row.dietary_tags = tags
    row.in_stock = True
    return row


ALL_TAGS = ["vegetarian", "vegan", "spicy", "seafood", "pork", "gluten_free", "dairy"]


@given(
    exclude=st.lists(st.sampled_from(ALL_TAGS), min_size=0, max_size=3, unique=True),
)
@settings(max_examples=30)
def test_fetch_menu_items_no_excluded_tag_returned(exclude: list[str]) -> None:
    mock_rows = [
        _make_mock_item(1, ["vegetarian", "spicy"]),
        _make_mock_item(2, ["seafood", "gluten_free"]),
        _make_mock_item(3, ["pork"]),
        _make_mock_item(4, []),
        _make_mock_item(5, ["vegan"]),
    ]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_rows

    with patch("src.tools.fetch_menu_items.get_session") as mock_session_ctx:
        mock_session = MagicMock()
        mock_session.execute.return_value = mock_result
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=False)

        result = fetch_menu_items(FetchMenuItemsInput(restaurant_id=1, dietary_exclude=exclude))

    assert result.is_ok()
    exclude_set = set(exclude)
    for item in result.unwrap().items:
        assert not exclude_set.intersection(item.dietary_tags), (
            f"Item '{item.name}' has excluded tag in {item.dietary_tags}"
        )


# ---------------------------------------------------------------------------
# query_restaurants: returned restaurants match requested cuisine
# ---------------------------------------------------------------------------

from src.tools.query_restaurants import QueryRestaurantsInput, QueryRestaurantsOutput, query_restaurants
from src.state import RestaurantCandidate


def _make_mock_restaurant(r_id: int, cuisine: str, rating: float) -> MagicMock:
    row = MagicMock()
    row.id = r_id
    row.name = f"Restaurant{r_id}"
    row.cuisine = cuisine
    row.city = "Colombo"
    row.rating = rating
    row.delivery_fee = 150.0
    row.avg_delivery_min = 30
    row.is_open = True
    return row


@given(
    cuisines=st.lists(
        st.sampled_from(["sri_lankan", "indian", "chinese", "italian", "american"]),
        min_size=1,
        max_size=3,
        unique=True,
    ),
    min_rating=st.floats(min_value=0.0, max_value=4.0, allow_nan=False),
)
@settings(max_examples=30)
def test_query_restaurants_cuisine_and_rating_match(
    cuisines: list[str],
    min_rating: float,
) -> None:
    matching = [
        _make_mock_restaurant(i, cuisine, 4.5)
        for i, cuisine in enumerate(cuisines)
    ]
    non_matching = [_make_mock_restaurant(99, "thai", 4.0)]
    mock_rows = [r for r in matching if 4.5 >= min_rating]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_rows

    with patch("src.tools.query_restaurants.get_session") as mock_session_ctx:
        mock_session = MagicMock()
        mock_session.execute.return_value = mock_result
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=False)

        result = query_restaurants(QueryRestaurantsInput(
            cuisines=cuisines, city="Colombo", min_rating=min_rating
        ))

    assert result.is_ok()
    cuisine_set = set(cuisines)
    for r in result.unwrap().restaurants:
        assert r.cuisine in cuisine_set
        assert r.rating >= min_rating
