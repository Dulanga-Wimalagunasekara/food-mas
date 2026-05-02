# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run all tests (inside Docker)
make test
# or: docker compose exec app pytest tests/ -v --tb=short

# Run a single test file
docker compose exec app pytest tests/test_planner.py -v

# Run a single test by name
docker compose exec app pytest tests/test_planner.py::test_parse_golden_inputs -v

# Run tests locally (Python 3.11+ required)
pip install -e ".[test]"
TRACE_DIR=/tmp/t LOG_DIR=/tmp/l CHECKPOINT_DB_PATH=/tmp/c.db pytest tests/ -v

# Lint
make lint   # runs ruff check src/ tests/

# Seed the database
make seed

# Start all services
make run

# Rebuild after Dockerfile/pyproject.toml changes
docker compose build app
```

`tests/llm_judge.py` is **not** collected by pytest automatically — run it separately:
```bash
docker compose exec app python tests/llm_judge.py
```

## Architecture

The system is a four-node LangGraph `StateGraph`. All inter-agent data flows through `GraphState` (`src/state.py`) — agents never call each other directly.

```
START → planner → restaurant_finder → menu_selector → order_validator → END
                       ↑  (relax constraints)  ↑  (retry)  ↑  (reselect)
                  ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ←
                                                        error → END
```

Each node is wrapped in a retry-counter function in `src/graph.py` (e.g. `planner_with_retry_count`). Routing is done by `route_after_*` functions that check `state.parsed`, `state.candidates`, etc. and increment `state.retries[agent]` on failure.

### State (`src/state.py`)
- **Do not use `X | None` syntax** — LangGraph calls `get_type_hints()` which fails on Python 3.9. Use `Optional[X]` throughout and do **not** add `from __future__ import annotations` to this file.
- `errors` uses `Annotated[list[AgentError], operator.add]` so multiple agents can append without overwriting.

### Tools (`src/tools/`)
All tools:
- Decorate with `@tool_with_retry(timeout_s, retries)` from `src/tools/base.py`
- Return `Ok(output)` or `Err(ToolError)` — **never raise**
- **Always read ORM attributes inside the `with get_session()` block** — SQLAlchemy expires objects when the session closes, causing "not bound to Session" errors if you access attributes outside the `with` block

### LLM (`src/llm.py`)
- `get_llm()` returns a singleton `ChatOllama` with `format="json"` (JSON mode enforced at the model level)
- `invoke_structured(llm, messages, schema, ...)` calls the LLM, parses JSON, validates against a Pydantic schema, and retries up to `max_retries` times — appending the validation error as a new user message on each retry

### Agents (`src/agents/`)
- **Planner**: runs `parse_request` (regex/keyword, no LLM) first; only calls LLM as fallback. This makes extraction injection-resistant.
- **Restaurant Finder**: queries DB via tool, then asks LLM to rank with `match_score`. Falls back to `rating / 5.0` if LLM fails.
- **Menu Selector**: LLM picks items at `temperature=0.3`. After the LLM responds, a deterministic post-check strips hallucinated item IDs (not in DB), re-fetches prices from DB (ignores LLM prices), and removes items with excluded dietary tags. Greedy fallback (cheapest mains) if LLM fails 3×.
- **Order Validator**: deterministic arithmetic only (subtotal + 10% tax + delivery). LLM writes a 2-sentence rationale and nothing else.

### DB (`src/db/`)
- `models.py`: `Restaurant` and `MenuItem` ORM models. `MenuItem.dietary_tags` is a JSON column storing a `list[str]`.
- `session.py`: `get_session()` context manager — commit on exit, rollback on exception.
- `seed.py`: idempotent — checks existence before inserting. Run with `python -m src.db.seed`.

### Config (`src/config.py`)
All config via env vars or `.env` file (`pydantic-settings`). Key vars: `MYSQL_HOST`, `MYSQL_PASSWORD`, `OLLAMA_HOST`, `OLLAMA_MODEL`, `CHECKPOINT_DB_PATH`, `TRACE_DIR`, `LOG_DIR`.

- Default model is `qwen2.5:1.5b` — chosen for CPU-only environments (~1 GB RAM). The 7b model requires GPU or ~6 GB free RAM; on CPU it will exceed timeout and the pipeline stalls.
- `ChatOllama` is configured with `request_timeout=120` (`src/llm.py`). If you switch to a larger model, increase this or add GPU passthrough to Docker.

### Tests
- `conftest.py` sets `TRACE_DIR`, `LOG_DIR`, `CHECKPOINT_DB_PATH` to temp dirs **before any src import** — this is critical because `logging_setup.py` runs `configure_logging()` at module level and tries to create those directories.
- Integration tests use `MemorySaver()` (not `SqliteSaver`) to avoid file I/O.
- All DB and LLM calls are mocked in unit and integration tests — no real MySQL or Ollama needed for `pytest`.

### Docker
- `PYTHONPATH=/app` is set in the Dockerfile so `import src` resolves when Streamlit runs `src/ui/app.py` from a different working directory.
- Build backend is `setuptools.build_meta` (not `setuptools.backends.legacy:build` — that requires setuptools ≥ 70.1 which may not be installed in the isolated build environment).
