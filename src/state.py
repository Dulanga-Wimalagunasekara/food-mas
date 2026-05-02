import operator
from typing import Annotated, Optional

from pydantic import BaseModel


class ParsedRequest(BaseModel):
    budget_lkr: float
    party_size: int
    cuisines: list[str]
    categories: list[str] = []
    dietary_exclude: list[str]
    dietary_require: list[str]
    spice_preference: Optional[str]
    city: str


class RestaurantCandidate(BaseModel):
    id: int
    name: str
    cuisine: str
    rating: float
    delivery_fee: float
    avg_delivery_min: int
    match_score: float


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
    rationale: str


class AgentError(BaseModel):
    agent: str
    kind: str
    message: str
    recoverable: bool


class GraphState(BaseModel):
    trace_id: str
    user_input: str
    parsed: Optional[ParsedRequest] = None
    sub_requests: list[ParsedRequest] = []          # set when request spans multiple restaurants
    candidates: list[RestaurantCandidate] = []
    chosen_restaurant_id: Optional[int] = None      # single-restaurant mode
    chosen_restaurant_ids: list[int] = []           # multi-restaurant mode
    selected_items: list[SelectedItem] = []
    order: Optional[OrderSummary] = None
    errors: Annotated[list[AgentError], operator.add] = []
    retries: dict[str, int] = {}
