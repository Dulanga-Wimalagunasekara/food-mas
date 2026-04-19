.PHONY: setup seed run test demo clean lint

setup:
	cp -n .env.example .env || true
	docker compose pull
	docker compose build

seed:
	docker compose exec app python -m src.db.seed

run:
	docker compose up

run-detached:
	docker compose up -d

test:
	docker compose exec app pytest tests/ -v --tb=short

demo:
	@echo "=== Demo: Running 3 example requests ==="
	docker compose exec app python -c "\
import asyncio, json, uuid\n\
from src.graph import build_graph\n\
from src.state import GraphState\n\
\n\
async def run_demo():\n\
    graph = build_graph()\n\
    requests = [\n\
        'I have LKR 3000 for two people, craving spicy Sri Lankan, no seafood',\n\
        'Budget 2500 rupees, want vegetarian Indian for one person',\n\
        'Looking for Italian food, about 4000 LKR for 3 people, no pork',\n\
    ]\n\
    for req in requests:\n\
        tid = str(uuid.uuid4())[:8]\n\
        state = GraphState(trace_id=tid, user_input=req)\n\
        print(f'\n--- Request: {req} ---')\n\
        async for event in graph.astream(state.model_dump(), config={'configurable': {'thread_id': tid}}):\n\
            for node, data in event.items():\n\
                print(f'  [{node}] done')\n\
        print(f'  Trace: traces/{tid}.jsonl')\n\
\n\
asyncio.run(run_demo())\n\
"

clean:
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -f data/checkpoints.db

lint:
	docker compose exec app python -m ruff check src/ tests/
