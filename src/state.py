from __future__ import annotations

import operator
from typing import Annotated

from pydantic import BaseModel, Field


class ParsedRequest(BaseModel):
    budget_lkr: float
    party_size: int
    cuisines: list[str]          # e.g. ["sri_lankan", "indian"]
    dietary_exclude: list[str]   # e.g. ["seafood", "pork"]
    dietary_require: list[str]   # e.g. ["vegetarian"]
    spice_preference: str | None # "mild" | "medium" | "hot" | None
    city: str


class RestaurantCandidate(BaseModel):
    id: int
    name: str
    cuisine: str
    rating: float
    delivery_fee: float
    avg_delivery_min: int
    match_score: float           # 0-1, computed by finder


class SelectedItem(BaseModel):
    item_id: int
    name: str
    price: float
    quantity: int
    dietary_tags: list[str]


class OrderSummary(BaseModel):
    restaurant_id: int
    restaurant_name: str
    items: list[SelectedItem]
    subtotal: float
    delivery_fee: float
    tax: float
    total: float
    within_budget: bool
    rationale: str               # short natural-language explanation


class AgentError(BaseModel):
    agent: str
    kind: str                    # "validation" | "tool_failure" | "llm_refusal"
    message: str
    recoverable: bool


class GraphState(BaseModel):
    trace_id: str
    user_input: str
    parsed: ParsedRequest | None = None
    candidates: list[RestaurantCandidate] = []
    chosen_restaurant_id: int | None = None
    selected_items: list[SelectedItem] = []
    order: OrderSummary | None = None
    errors: Annotated[list[AgentError], operator.add] = []
    retries: dict[str, int] = {}
