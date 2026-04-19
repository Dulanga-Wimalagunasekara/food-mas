# Architecture: Smart Food Ordering Multi-Agent System

## Overview

The system is a four-agent pipeline built on LangGraph. Agents communicate exclusively through a shared `GraphState` object — no agent calls another directly. Each agent reads from state, calls a typed tool, and writes its result back to a designated state field. LangGraph's conditional edges handle routing, retries, and escalation to an error sink.

All LLM inference runs locally via Ollama (`qwen2.5:7b-instruct`). No external paid APIs are used.

---

## Graph Topology

```
START
  │
  ▼
┌───────────────────────────────────────────────────────────┐
│ planner                                                   │
│  Tool: parse_request (regex/keyword, LLM fallback)        │
│  Writes: state.parsed (ParsedRequest)                     │
└───────────────────────────────────────────────────────────┘
  │  state.parsed is not None  →  restaurant_finder
  │  parsed is None, retries < 2  →  planner (retry)
  │  retries exhausted  →  error
  ▼
┌───────────────────────────────────────────────────────────┐
│ restaurant_finder                                         │
│  Tool: query_restaurants (SQLAlchemy parameterized query) │
│  LLM: ranks candidates with match_score                   │
│  Writes: state.candidates (list[RestaurantCandidate])     │
└───────────────────────────────────────────────────────────┘
  │  candidates not empty  →  menu_selector
  │  empty, retries < 1  →  planner (relax constraints)
  │  retries exhausted  →  error
  ▼
┌───────────────────────────────────────────────────────────┐
│ menu_selector                                             │
│  Tool: fetch_menu_items (SQLAlchemy, in-stock filter)     │
│  LLM: selects item combo within budget (temp=0.3)         │
│  Post-check: strips hallucinated IDs, dietary violations  │
│  Greedy fallback: cheapest mains if LLM fails 3×          │
│  Writes: state.selected_items (list[SelectedItem])        │
└───────────────────────────────────────────────────────────┘
  │  selected_items not empty  →  order_validator
  │  empty, retries < 1  →  restaurant_finder (retry)
  │  retries exhausted  →  error
  ▼
┌───────────────────────────────────────────────────────────┐
│ order_validator                                           │
│  Tool: validate_order (recomputes totals, stock, tags)    │
│  LLM: writes 2-sentence rationale only                    │
│  Writes: state.order (OrderSummary)                       │
└───────────────────────────────────────────────────────────┘
  │  order is not None and within_budget  →  END
  │  over budget, retries < 1  →  menu_selector (reselect)
  │  retries exhausted  →  END (returns what we have)
  ▼
END

  (any node)  →  error  →  END
```

---

## Agent Details

### Agent 1 — Planner

**Purpose:** Convert free-text user input into a structured `ParsedRequest`.

**Strategy:** Rule-based extraction first (deterministic, injection-resistant), LLM fallback only when rules fail. The rule engine uses regex patterns and keyword maps:

- Budget: patterns like `LKR 3000`, `Rs 4000`, `2500 rupees` with lookahead to avoid consuming adjacent tokens
- Party size: numeric and word forms (`"for two"`, `"3 people"`)
- Cuisines: keyword-to-canonical mapping (`"sri lankan"` → `"sri_lankan"`)
- Dietary: inclusion (`"vegetarian"`) and exclusion (`"no seafood"`, `"no pork"`)
- Spice: `"spicy"` → `"hot"`, `"mild"` → `"mild"`, etc.

**State contract:**
- Reads: `state.user_input`, `state.errors`
- Writes: `state.parsed`

---

### Agent 2 — Restaurant Finder

**Purpose:** Find restaurants that match cuisine and location constraints, ranked by fit.

**Strategy:** Query MySQL via `query_restaurants` tool (SQLAlchemy parameterized `select()` — no string interpolation). Results are passed to the LLM for ranking with `match_score` (0–1). If the LLM fails, falls back to `rating / 5.0` as the score.

**State contract:**
- Reads: `state.parsed`
- Writes: `state.candidates`, `state.chosen_restaurant_id`

---

### Agent 3 — Menu Selector

**Purpose:** Select a combination of menu items that fits the budget and satisfies dietary constraints.

**Strategy:** Fetch all in-stock items for the chosen restaurant (dietary exclusions filtered at Python layer, not SQL). LLM selects an item combination at temperature=0.3. Deterministic post-check:
1. Drop any `item_id` not present in the DB fetch result
2. Re-fetch prices from DB (ignore LLM-reported prices to prevent hallucination)
3. Strip items whose `dietary_tags` overlap with `parsed.dietary_exclude`
4. Enforce budget: `subtotal + delivery_fee ≤ budget_lkr`

If LLM fails 3×, greedy fallback selects cheapest main-course items up to budget.

**State contract:**
- Reads: `state.parsed`, `state.candidates`, `state.chosen_restaurant_id`
- Writes: `state.selected_items`

---

### Agent 4 — Order Validator

**Purpose:** Verify the order is correct and produce a human-readable rationale.

**Strategy:** `validate_order` tool re-queries the DB for live stock status and dietary tags (defensive check in case items sold out between selection and validation). Arithmetic:
- `subtotal = sum(item.price × item.quantity)`
- `tax = subtotal × 0.10`
- `total = subtotal + delivery_fee + tax`
- `within_budget = total ≤ parsed.budget_lkr`

LLM writes only a 2-sentence rationale — no arithmetic delegated to the LLM.

**State contract:**
- Reads: `state.parsed`, `state.selected_items`, `state.candidates`, `state.chosen_restaurant_id`
- Writes: `state.order`

---

## State Schema

```python
class GraphState(BaseModel):
    trace_id: str                              # UUID prefix for log correlation
    user_input: str                            # Raw user text
    parsed: Optional[ParsedRequest]            # Set by planner
    candidates: list[RestaurantCandidate]      # Set by restaurant_finder
    chosen_restaurant_id: Optional[int]        # Set by restaurant_finder
    selected_items: list[SelectedItem]         # Set by menu_selector
    order: Optional[OrderSummary]              # Set by order_validator
    errors: Annotated[list[AgentError], operator.add]  # Appended by any agent
    retries: dict[str, int]                    # Incremented by retry wrappers
```

`errors` uses `operator.add` as the reducer so multiple agents can append errors concurrently without overwrite.

---

## Tool Design

All tools follow the **Result type** contract — they never raise exceptions:

```python
Result = Union[Ok[T], Err[ToolError]]

def my_tool(input: MyInput) -> Result:
    try:
        ...
        return Ok(result)
    except Exception as e:
        return Err(ToolError(kind="db_error", message=str(e), recoverable=True))
```

The `tool_with_retry` decorator wraps each tool with:
- Configurable timeout (default 10s)
- Configurable retry count (default 2)
- Returns `Err(ToolError)` after exhaustion — never propagates exceptions to the graph

This guarantees the LangGraph state machine always reaches `END`, even during a MySQL outage.

---

## Retry and Escalation Logic

| Node | Success condition | Retry condition | Escalation |
|---|---|---|---|
| planner | `state.parsed is not None` | `retries["planner"] < 2` | → error node |
| restaurant_finder | `state.candidates` not empty | `retries["finder"] < 1` → loops back to **planner** (relaxes constraints) | → error node |
| menu_selector | `state.selected_items` not empty | `retries["selector"] < 1` → loops back to **restaurant_finder** | → error node |
| order_validator | `state.order.within_budget` | `retries["validator"] < 1` → loops back to **menu_selector** | → END (returns over-budget order) |

---

## Persistence and Observability

**SQLite checkpoints:** LangGraph persists the full `GraphState` after every node execution via `SqliteSaver`. Runs are resumable if interrupted. The checkpoint DB path is configured via `settings.checkpoint_db_path`.

**JSONL traces:** Every state transition is appended to `traces/{trace_id}.jsonl`. Each record includes:
- `node` — agent name
- `status` — `start` or `end`
- `latency_ms` — wall-clock time for the node
- `input_hash` / `output_hash` — SHA-256 prefix of state for diffing
- `errors` — any `AgentError` objects appended during this node

Traces can be replayed offline:
```python
from src.logging_setup import replay_trace
for record in replay_trace("abc12345"):
    print(record["node"], record["status"], record.get("latency_ms"))
```

---

## Security Properties

| Threat | Mitigation |
|---|---|
| Prompt injection via user input | Planner uses regex/keyword rules — LLM never sees raw user text during field extraction |
| SQL injection | SQLAlchemy parameterized `select()` throughout — no string interpolation in queries |
| LLM hallucinated item IDs | Menu selector verifies all IDs against DB fetch; unrecognized IDs are dropped silently |
| LLM hallucinated prices | Menu selector re-fetches all prices from DB; LLM-reported prices are ignored |
| Dietary constraint violation | Menu selector strips items with excluded tags after LLM selection; validator rechecks from DB |
| Tool exception crashing graph | All tools return `Ok | Err` — exceptions are caught and wrapped; graph always reaches END |

---

## Docker Compose Services

| Service | Image | Role |
|---|---|---|
| `mysql` | mysql:8.4 | Primary data store (restaurants, menu items) |
| `ollama` | ollama/ollama | LLM inference server |
| `ollama-pull` | ollama/ollama | One-shot model download on first start |
| `app` | (local build) | Seed DB + run Streamlit UI |

The `app` service depends on `mysql` and `ollama` being healthy (via `condition: service_healthy`) before starting.
