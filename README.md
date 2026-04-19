# Smart Food Ordering Assistant — Multi-Agent System

A locally-hosted multi-agent food ordering system built with LangGraph, Ollama, and MySQL. Given a natural-language request like *"LKR 3000 for two people, spicy Sri Lankan, no seafood"*, the system autonomously parses intent, queries restaurants, selects optimal menu items, validates the order, and returns a structured summary — all running on local SLMs with no paid APIs.

## Architecture

```
User Input
    │
    ▼
┌─────────┐    ┌──────────────────┐    ┌───────────────┐    ┌─────────────────┐
│ Planner │───▶│ Restaurant Finder│───▶│ Menu Selector │───▶│ Order Validator │
│ Agent 1 │    │    Agent 2       │    │   Agent 3     │    │    Agent 4      │
└─────────┘    └──────────────────┘    └───────────────┘    └─────────────────┘
    │                  │                       │                      │
    ▼                  ▼                       ▼                      ▼
parse_request    query_restaurants      fetch_menu_items       validate_order
  (tool)            (tool)                 (tool)                 (tool)
    │                  │                       │                      │
    └──────────────────┴───────────────────────┴──────────────────────┘
                                    │
                               MySQL 8 + SQLite (checkpoints)
```

Each agent follows a loop: system prompt → Ollama JSON mode → Pydantic validation → retry on failure. Conditional edges in LangGraph handle escalation (e.g. no restaurants found → relax constraints and retry).

See `docs/architecture.md` for full workflow details.

## Quick Start

**Prerequisites:** Docker and Docker Compose only.

```bash
git clone <repo-url> && cd food-mas
cp .env.example .env
docker compose up
```

The first run pulls `qwen2.5:7b-instruct` (~4 GB) — allow 5–10 minutes on first start. Subsequent starts are fast.

Open **http://localhost:8501** in your browser.

## Run Tests

```bash
make test
# or directly:
docker compose exec app pytest tests/ -v
```

Locally (requires Python 3.11+):
```bash
pip install -e ".[test]"
pytest tests/ -v
```

## Demo

```bash
make demo
```

Runs three example requests end-to-end and prints trace IDs. Each run writes a JSONL trace to `traces/{trace_id}.jsonl`.

## Makefile Targets

| Command | Description |
|---|---|
| `make setup` | Copy `.env.example`, pull images, build |
| `make seed` | Re-seed the MySQL database |
| `make run` | Start all services |
| `make test` | Run full pytest suite inside container |
| `make demo` | Run 3 example requests with trace output |
| `make clean` | Remove containers, volumes, cached files |

## Resilience Testing

To verify recovery from a MySQL failure mid-run:

```bash
# In one terminal, start a request in the UI
# In another terminal, pause MySQL
docker compose pause mysql
# Observe the tool returning Err and the agent logging the failure
# Resume MySQL
docker compose unpause mysql
# The graph retries and completes the order
```

Tool errors are returned as `Err(ToolError)` (never raised), so the graph always reaches a terminal state.

## Trace Replay

Every run writes per-node state transitions to `traces/{trace_id}.jsonl`:

```python
from src.logging_setup import replay_trace
records = replay_trace("abc12345")
for r in records:
    print(r["node"], r["status"], r.get("latency_ms"))
```

## Project Structure

```
src/
  config.py          # Pydantic BaseSettings, env-driven
  state.py           # GraphState and all inter-agent Pydantic models
  llm.py             # Ollama client factory with validation-retry wrapper
  logging_setup.py   # structlog JSON logging + JSONL trace writer
  graph.py           # LangGraph nodes, conditional edges, SqliteSaver
  agents/            # planner, restaurant_finder, menu_selector, order_validator
  tools/             # parse_request, query_restaurants, fetch_menu_items, validate_order
  db/                # SQLAlchemy models, session, idempotent seed (15 restaurants)
  ui/app.py          # Streamlit dark-theme UI with live agent trace panel
tests/
  conftest.py              # env overrides, shared fixtures
  test_tools_properties.py # Hypothesis property-based tests
  test_planner.py          # Planner golden-input tests
  test_restaurant_finder.py
  test_menu_selector.py
  test_order_validator.py
  test_integration.py      # Full graph runs with mocked LLM and DB
  test_adversarial.py      # Prompt injection, SQL injection, edge cases
  llm_judge.py             # Standalone LLM-as-judge evaluator (run separately)
```

## Tech Stack

| Component | Version |
|---|---|
| Python | 3.11 |
| LangGraph | ≥ 0.2.50 |
| langchain-ollama | ≥ 0.2.0 |
| Pydantic | ≥ 2.9 |
| SQLAlchemy | ≥ 2.0 |
| MySQL | 8.4 |
| Ollama model | qwen2.5:7b-instruct |
| Streamlit | ≥ 1.40 |

## Design Decisions

- **No paid APIs.** All LLM inference runs via local Ollama.
- **Rule-based parsing first.** The Planner's `parse_request` tool uses regex and keyword matching rather than the LLM for deterministic, injection-resistant field extraction. The LLM is only invoked as a fallback.
- **Deterministic post-checks.** Menu Selector verifies item IDs, prices, and dietary tags in Python after the LLM returns selections — hallucinated IDs are silently dropped.
- **Result type instead of exceptions.** All tools return `Ok | Err` so the graph always reaches a terminal state, even when MySQL is unavailable mid-run.
- **SQLite checkpoints.** LangGraph state is persisted to SQLite so runs are resumable and inspectable.
