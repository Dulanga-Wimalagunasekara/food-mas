from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger

from src.config import settings


def _add_timestamp(_: WrappedLogger, __: str, event_dict: EventDict) -> EventDict:
    event_dict["ts"] = time.time()
    return event_dict


def configure_logging() -> None:
    Path(settings.log_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.trace_dir).mkdir(parents=True, exist_ok=True)

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            _add_timestamp,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


def get_logger(**kwargs: Any) -> structlog.BoundLogger:
    return structlog.get_logger(**kwargs)


def hash_state(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


class TraceWriter:
    """Appends one JSON line per state transition to traces/{trace_id}.jsonl."""

    def __init__(self, trace_id: str) -> None:
        self._path = Path(settings.trace_dir) / f"{trace_id}.jsonl"
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, record: dict[str, Any]) -> None:
        with self._path.open("a") as f:
            f.write(json.dumps(record, default=str) + "\n")


def node_logger(trace_id: str, agent: str, node: str) -> structlog.BoundLogger:
    return get_logger().bind(trace_id=trace_id, agent=agent, node=node)


def replay_trace(trace_id: str) -> list[dict[str, Any]]:
    """Load a JSONL trace file and return all recorded state transitions.

    Args:
        trace_id: The trace identifier used when the run was executed.

    Returns:
        Ordered list of state-transition records from the trace file.

    Raises:
        FileNotFoundError: If no trace file exists for the given trace_id.
    """
    path = Path(settings.trace_dir) / f"{trace_id}.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"No trace found for trace_id={trace_id}")
    records = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


configure_logging()
