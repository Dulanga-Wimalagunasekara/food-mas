from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Literal

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from src.agents.menu_selector import run_menu_selector
from src.agents.order_validator import run_order_validator
from src.agents.planner import run_planner
from src.agents.restaurant_finder import run_restaurant_finder
from src.config import settings
from src.state import GraphState

MAX_PLANNER_RETRIES = 2
MAX_FINDER_RETRIES = 1
MAX_SELECTOR_RETRIES = 1


# ---------------------------------------------------------------------------
# Routing functions
# ---------------------------------------------------------------------------

def route_after_planner(state: GraphState) -> Literal["restaurant_finder", "planner", "error"]:
    if state.parsed is not None:
        return "restaurant_finder"
    retries = state.retries.get("planner", 0)
    if retries < MAX_PLANNER_RETRIES:
        return "planner"
    return "error"


def route_after_finder(state: GraphState) -> Literal["menu_selector", "planner", "error"]:
    if state.candidates:
        return "menu_selector"
    # Escalation: relax constraints by looping back to planner
    retries = state.retries.get("finder", 0)
    if retries < MAX_FINDER_RETRIES:
        return "planner"
    return "error"


def route_after_selector(
    state: GraphState,
) -> Literal["order_validator", "restaurant_finder", "error"]:
    if state.selected_items:
        return "order_validator"
    retries = state.retries.get("selector", 0)
    if retries < MAX_SELECTOR_RETRIES:
        return "restaurant_finder"
    return "error"


def route_after_validator(
    state: GraphState,
) -> Literal[END, "menu_selector"]:  # type: ignore[valid-type]
    if state.order is None:
        return "menu_selector"
    if not state.order.within_budget:
        retries = state.retries.get("validator", 0)
        if retries < MAX_SELECTOR_RETRIES:
            return "menu_selector"
    return END


# ---------------------------------------------------------------------------
# Error sink node
# ---------------------------------------------------------------------------

def error_node(state: GraphState) -> dict:
    from src.logging_setup import get_logger
    log = get_logger().bind(trace_id=state.trace_id)
    log.error("graph.terminal_error", errors=[e.model_dump() for e in state.errors])
    return {}


# ---------------------------------------------------------------------------
# Retry-counter wrappers
# ---------------------------------------------------------------------------

def planner_with_retry_count(state: GraphState) -> dict:
    result = run_planner(state)
    if result.get("parsed") is None:
        retries = dict(state.retries)
        retries["planner"] = retries.get("planner", 0) + 1
        result["retries"] = retries
    return result


def finder_with_retry_count(state: GraphState) -> dict:
    result = run_restaurant_finder(state)
    if not result.get("candidates"):
        retries = dict(state.retries)
        retries["finder"] = retries.get("finder", 0) + 1
        result["retries"] = retries
    return result


def selector_with_retry_count(state: GraphState) -> dict:
    result = run_menu_selector(state)
    if not result.get("selected_items"):
        retries = dict(state.retries)
        retries["selector"] = retries.get("selector", 0) + 1
        result["retries"] = retries
    return result


def validator_with_retry_count(state: GraphState) -> dict:
    result = run_order_validator(state)
    if result.get("order") is None or (result.get("order") and not result["order"].within_budget):
        retries = dict(state.retries)
        retries["validator"] = retries.get("validator", 0) + 1
        result["retries"] = retries
    return result


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_graph(checkpointer=None):
    if checkpointer is None:
        Path(settings.checkpoint_db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(settings.checkpoint_db_path, check_same_thread=False)
        checkpointer = SqliteSaver(conn)

    builder = StateGraph(GraphState)

    builder.add_node("planner", planner_with_retry_count)
    builder.add_node("restaurant_finder", finder_with_retry_count)
    builder.add_node("menu_selector", selector_with_retry_count)
    builder.add_node("order_validator", validator_with_retry_count)
    builder.add_node("error", error_node)

    builder.add_edge(START, "planner")

    builder.add_conditional_edges(
        "planner",
        route_after_planner,
        {"restaurant_finder": "restaurant_finder", "planner": "planner", "error": "error"},
    )
    builder.add_conditional_edges(
        "restaurant_finder",
        route_after_finder,
        {"menu_selector": "menu_selector", "planner": "planner", "error": "error"},
    )
    builder.add_conditional_edges(
        "menu_selector",
        route_after_selector,
        {"order_validator": "order_validator", "restaurant_finder": "restaurant_finder", "error": "error"},
    )
    builder.add_conditional_edges(
        "order_validator",
        route_after_validator,
        {END: END, "menu_selector": "menu_selector"},
    )
    builder.add_edge("error", END)

    return builder.compile(checkpointer=checkpointer)
