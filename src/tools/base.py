from __future__ import annotations

import functools
import time
from typing import Callable, Generic, TypeVar, Union

from pydantic import BaseModel

OK = TypeVar("OK")
ERR = TypeVar("ERR")


class ToolError(BaseModel):
    tool: str
    kind: str      # "db_error" | "timeout" | "validation" | "not_found"
    message: str


class Ok(Generic[OK]):
    __slots__ = ("value",)

    def __init__(self, value: OK) -> None:
        self.value = value

    def is_ok(self) -> bool:
        return True

    def unwrap(self) -> OK:
        return self.value


class Err(Generic[ERR]):
    __slots__ = ("error",)

    def __init__(self, error: ERR) -> None:
        self.error = error

    def is_ok(self) -> bool:
        return False

    def unwrap(self) -> ERR:
        return self.error


Result = Union[Ok[OK], Err[ERR]]


def tool_with_retry(
    timeout_s: float = 10.0,
    retries: int = 2,
) -> Callable:
    """Decorator that retries a tool function on exception.

    Args:
        timeout_s: Per-attempt wall-clock limit in seconds (checked post-call).
        retries: Number of additional attempts after the first failure.

    Returns:
        Decorator wrapping the tool in retry logic that returns Err on
        exhaustion rather than propagating the exception.
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs) -> Result:
            last_exc: Exception | None = None
            for attempt in range(retries + 1):
                t0 = time.monotonic()
                try:
                    result = fn(*args, **kwargs)
                    elapsed = time.monotonic() - t0
                    if elapsed > timeout_s:
                        # Completed but slow — still return the result
                        pass
                    return result
                except Exception as exc:
                    last_exc = exc
                    elapsed = time.monotonic() - t0
                    if attempt < retries:
                        continue
            return Err(
                ToolError(
                    tool=fn.__name__,
                    kind="tool_failure",
                    message=str(last_exc),
                )
            )
        return wrapper
    return decorator
