FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ".[test]"

COPY src/ ./src/
COPY tests/ ./tests/

RUN mkdir -p /app/data /app/traces /app/logs

# Seed DB and launch UI
CMD ["sh", "-c", "python -m src.db.seed && streamlit run src/ui/app.py --server.port=8501 --server.address=0.0.0.0"]
