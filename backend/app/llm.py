"""The ONLY gateway to Claude (shared, FROZEN; owner Dev 1). Every call is logged to `ai_runs` with tokens and $ (F9/F10).

    msg = call_claude("digest", settings.model_fast, matter_id=1, messages=[...], max_tokens=4000)
    parsed = call_claude_parsed("extract", settings.model_main, MyPydanticModel, matter_id=1, messages=[...])
    with stream_claude("ask", settings.model_main, matter_id=1, user_id=2, messages=[...], tools=[...]) as stream: ...
    log_cache_hit("digest", settings.model_fast, matter_id=1, saved_usd=0.004)   # a skipped (cached) call
    log_local_run("embed", "BAAI/bge-base-en-v1.5", matter_id=1, duration_ms=1234)

All calls go through the beta Messages namespace so the Opus server-side refusal fallback ("default") can be enabled.
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any, Iterator, TypeVar

import anthropic

from .config import settings
from .db import connect, now_iso

# USD per million tokens. cache_write = 1.25x input (5-minute TTL); cache_read per model.
PRICES: dict[str, dict[str, float]] = {
    "claude-opus-5-5": {"input": 4.00, "output": 20.00, "cache_read": 0.20, "cache_write": 5.00},
    "claude-sonnet-5-5": {"input": 2.00, "output": 10.00, "cache_read": 0.20, "cache_write": 2.50},
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00, "cache_read": 0.10, "cache_write": 1.25},
}
FALLBACK_BETA = "server-side-fallback-2026-07-01"
# Models that accept `fallbacks: "default"` on the Claude API.
_FALLBACK_MODELS = {"claude-opus-5-5", "claude-sonnet-5-5"}

_client: anthropic.Anthropic | None = None
M = TypeVar("M")


class LLMNotConfigured(RuntimeError):
    pass


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not settings.anthropic_api_key:
            raise LLMNotConfigured("ANTHROPIC_API_KEY is not set in .env")
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key, max_retries=3)
    return _client


def price_of(model: str, usage: Any) -> float:
    p = PRICES.get(model) or PRICES.get(_base_model(model)) or PRICES["claude-opus-5-5"]
    inp = getattr(usage, "input_tokens", 0) or 0
    out = getattr(usage, "output_tokens", 0) or 0
    cr = getattr(usage, "cache_read_input_tokens", 0) or 0
    cw = getattr(usage, "cache_creation_input_tokens", 0) or 0
    return (inp * p["input"] + out * p["output"] + cr * p["cache_read"] + cw * p["cache_write"]) / 1_000_000


def _base_model(model: str) -> str:
    for known in PRICES:
        if model.startswith(known):
            return known
    return model


def _log(purpose: str, model: str, usage: Any, *, matter_id: int | None, user_id: int | None,
         duration_ms: int | None, cost: float, cache_hit: bool = False, saved_usd: float = 0.0) -> None:
    with connect() as db:
        db.execute(
            """INSERT INTO ai_runs(matter_id, user_id, purpose, model, input_tokens, output_tokens, cache_read_tokens,
                                   cache_write_tokens, cost_usd, duration_ms, cache_hit, saved_usd, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (matter_id, user_id, purpose, model,
             getattr(usage, "input_tokens", 0) or 0, getattr(usage, "output_tokens", 0) or 0,
             getattr(usage, "cache_read_input_tokens", 0) or 0, getattr(usage, "cache_creation_input_tokens", 0) or 0,
             round(cost, 6), duration_ms, int(cache_hit), round(saved_usd, 6), now_iso()))


def _request_kwargs(model: str, kwargs: dict[str, Any]) -> dict[str, Any]:
    kw = dict(kwargs)
    kw.setdefault("max_tokens", 16000)
    if _base_model(model) in _FALLBACK_MODELS and "fallbacks" not in kw:
        kw["fallbacks"] = "default"
        kw["betas"] = list({*kw.get("betas", []), FALLBACK_BETA})
    return kw


def _check(msg: Any) -> Any:
    if getattr(msg, "stop_reason", None) == "refusal":
        raise RuntimeError("Claude declined this request (refusal)")
    return msg


def call_claude(purpose: str, model: str, *, matter_id: int | None = None, user_id: int | None = None,
                **kwargs: Any) -> Any:
    """Non-streaming request. Returns the Message. kwargs go straight to client.beta.messages.create."""
    t0 = time.monotonic()
    msg = client().beta.messages.create(model=model, **_request_kwargs(model, kwargs))
    served = getattr(msg, "model", model) or model
    _log(purpose, served, msg.usage, matter_id=matter_id, user_id=user_id,
         duration_ms=int((time.monotonic() - t0) * 1000), cost=price_of(served, msg.usage))
    return _check(msg)


def call_claude_parsed(purpose: str, model: str, output_format: type[M], *, matter_id: int | None = None,
                       user_id: int | None = None, **kwargs: Any) -> tuple[M, Any]:
    """Structured output (Pydantic). Returns (parsed_output, message)."""
    t0 = time.monotonic()
    msg = client().beta.messages.parse(model=model, output_format=output_format, **_request_kwargs(model, kwargs))
    served = getattr(msg, "model", model) or model
    _log(purpose, served, msg.usage, matter_id=matter_id, user_id=user_id,
         duration_ms=int((time.monotonic() - t0) * 1000), cost=price_of(served, msg.usage))
    _check(msg)
    return msg.parsed_output, msg


@contextmanager
def stream_claude(purpose: str, model: str, *, matter_id: int | None = None, user_id: int | None = None,
                  **kwargs: Any) -> Iterator[Any]:
    """Streaming request; logs usage when the stream completes. Yields the SDK MessageStream."""
    t0 = time.monotonic()
    with client().beta.messages.stream(model=model, **_request_kwargs(model, kwargs)) as stream:
        yield stream
        final = stream.get_final_message()
    served = getattr(final, "model", model) or model
    _log(purpose, served, final.usage, matter_id=matter_id, user_id=user_id,
         duration_ms=int((time.monotonic() - t0) * 1000), cost=price_of(served, final.usage))


def last_cost(matter_id: int | None, since_id: int) -> float:
    with connect() as db:
        row = db.execute("SELECT COALESCE(SUM(cost_usd),0) FROM ai_runs WHERE id > ? AND (? IS NULL OR matter_id = ?)",
                         (since_id, matter_id, matter_id)).fetchone()
    return float(row[0])


def max_run_id() -> int:
    with connect() as db:
        return int(db.execute("SELECT COALESCE(MAX(id),0) FROM ai_runs").fetchone()[0])


def log_cache_hit(purpose: str, model: str, *, matter_id: int | None = None, saved_usd: float = 0.0) -> None:
    """Record that a call was SKIPPED because its input hash was cached (cost 0, estimated savings)."""
    _log(purpose, model, None, matter_id=matter_id, user_id=None, duration_ms=0, cost=0.0,
         cache_hit=True, saved_usd=saved_usd)


def log_local_run(purpose: str, model: str, *, matter_id: int | None = None, duration_ms: int = 0) -> None:
    """Local (free) model runs, e.g. embeddings, logged at $0 so the cost view shows them."""
    _log(purpose, model, None, matter_id=matter_id, user_id=None, duration_ms=duration_ms, cost=0.0)


def text_of(msg: Any) -> str:
    return "".join(getattr(b, "text", "") for b in msg.content if getattr(b, "type", "") == "text")
