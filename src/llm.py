from __future__ import annotations

import json
import time
from typing import Any, TypeVar

from langchain_ollama import ChatOllama
from pydantic import BaseModel, ValidationError

from src.config import settings
from src.logging_setup import get_logger

logger = get_logger()

T = TypeVar("T", bound=BaseModel)

_PRIMARY_MODEL: ChatOllama | None = None
_FALLBACK_MODEL: ChatOllama | None = None


def _primary() -> ChatOllama:
    global _PRIMARY_MODEL
    if _PRIMARY_MODEL is None:
        _PRIMARY_MODEL = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_host,
            format="json",
            temperature=0.1,
        )
    return _PRIMARY_MODEL


def _fallback() -> ChatOllama:
    global _FALLBACK_MODEL
    if _FALLBACK_MODEL is None:
        _FALLBACK_MODEL = ChatOllama(
            model=settings.ollama_fallback_model,
            base_url=settings.ollama_host,
            format="json",
            temperature=0.1,
        )
    return _FALLBACK_MODEL


def get_llm(temperature: float = 0.1, use_fallback: bool = False) -> ChatOllama:
    """Return a ChatOllama instance with JSON mode enabled.

    Args:
        temperature: Sampling temperature (0.0–1.0).
        use_fallback: If True, use the fallback model instead of primary.

    Returns:
        Configured ChatOllama client.
    """
    model = _fallback() if use_fallback else _primary()
    model.temperature = temperature
    return model


def invoke_structured(
    llm: ChatOllama,
    messages: list[dict[str, str]],
    schema: type[T],
    trace_id: str,
    agent: str,
    max_retries: int = 2,
) -> T:
    """Call the LLM and parse its JSON output into a Pydantic model.

    Retries up to max_retries times on JSON decode errors or schema
    validation failures. On persistent failure, raises the last exception.

    Args:
        llm: The ChatOllama client to use.
        messages: Chat messages in OpenAI format.
        schema: Pydantic model class to validate the response against.
        trace_id: Trace ID for structured logging.
        agent: Agent name for structured logging.
        max_retries: Maximum number of retry attempts after initial call.

    Returns:
        Validated Pydantic model instance.

    Raises:
        ValueError: If the LLM response cannot be parsed after all retries.
    """
    bound = logger.bind(trace_id=trace_id, agent=agent, schema=schema.__name__)
    last_exc: Exception | None = None

    for attempt in range(max_retries + 1):
        t0 = time.monotonic()
        try:
            lc_messages = _to_langchain_messages(messages)
            response = llm.invoke(lc_messages)
            raw = response.content if hasattr(response, "content") else str(response)
            latency_ms = int((time.monotonic() - t0) * 1000)

            parsed_json = json.loads(raw)
            result = schema.model_validate(parsed_json)

            bound.info(
                "llm.success",
                attempt=attempt,
                latency_ms=latency_ms,
            )
            return result

        except (json.JSONDecodeError, ValidationError, Exception) as exc:
            latency_ms = int((time.monotonic() - t0) * 1000)
            last_exc = exc
            bound.warning(
                "llm.retry",
                attempt=attempt,
                latency_ms=latency_ms,
                error=str(exc),
            )

            if attempt < max_retries:
                error_context = {
                    "role": "user",
                    "content": (
                        f"Your previous response caused a validation error: {exc}. "
                        f"Return ONLY valid JSON matching the {schema.__name__} schema. "
                        "No prose, no markdown, no extra keys."
                    ),
                }
                messages = messages + [error_context]

    raise ValueError(
        f"LLM failed to produce valid {schema.__name__} after {max_retries + 1} attempts: {last_exc}"
    )


def _to_langchain_messages(messages: list[dict[str, str]]) -> list[Any]:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    mapping = {"system": SystemMessage, "user": HumanMessage, "assistant": AIMessage}
    return [mapping.get(m["role"], HumanMessage)(content=m["content"]) for m in messages]
