"""Shared test fixtures and environment setup."""
from __future__ import annotations

import os
import tempfile

# Override Docker paths before any src imports so logging_setup doesn't try /app
_tmp = tempfile.mkdtemp(prefix="foodmas_test_")
os.environ.setdefault("TRACE_DIR", os.path.join(_tmp, "traces"))
os.environ.setdefault("LOG_DIR", os.path.join(_tmp, "logs"))
os.environ.setdefault("CHECKPOINT_DB_PATH", os.path.join(_tmp, "checkpoints.db"))
os.environ.setdefault("MYSQL_HOST", "localhost")
os.environ.setdefault("OLLAMA_HOST", "http://localhost:11434")
