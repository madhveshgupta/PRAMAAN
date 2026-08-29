"""The only door to the LLM (invariant #5).

Everything model-related passes through here, which is what makes swapping the model a
one-file change rather than a hunt through the codebase. That claim was tested on
2026-09-02: switching the provider touched this file, `config.py` and `requirements.txt`,
and nothing else in `api/`, `worker/` or `ml/`.

The provider is **Google Gemini**, through Google's unified GenAI SDK.

Two behaviours worth knowing:

* **Response caching by prompt hash.** Committed to disk, so the demo survives a fresh
  clone and a dead network.
* **DEMO_MODE serves cache only.** A cache miss raises rather than quietly reaching for
  the network — the whole point is that the demo cannot depend on connectivity.
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from api.app.config import get_settings

log = logging.getLogger("pramaan.llm")

CACHE_DIR = Path(__file__).resolve().parents[3] / "ml" / "llm_cache"


class LLMUnavailable(RuntimeError):
    """No API key, or DEMO_MODE with a cache miss. Callers degrade; they do not guess."""


def _cache_key(model: str, prompt: str, system: str) -> str:
    return hashlib.sha256(f"{model}\x00{system}\x00{prompt}".encode()).hexdigest()[:32]


def _cached(key: str) -> str | None:
    path = CACHE_DIR / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text())["response"]
    return None


def _store(key: str, prompt: str, response: str) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / f"{key}.json").write_text(json.dumps(
        {"prompt": prompt[:2000], "response": response}, indent=2))


# Rough per-run accounting so the cost question has an answer before anyone asks it.
USAGE = {"calls": 0, "cache_hits": 0, "input_tokens": 0, "output_tokens": 0}


def complete(prompt: str, *, system: str = "", max_tokens: int = 4096,
             temperature: float = 0.0) -> str:
    settings = get_settings()
    key = _cache_key(settings.llm_model, prompt, system)

    hit = _cached(key)
    if hit is not None:
        USAGE["cache_hits"] += 1
        return hit

    if settings.demo_mode:
        raise LLMUnavailable(
            "DEMO_MODE is on and this prompt is not cached. Refusing to call the network — "
            "pre-compute the demo documents instead.")
    if not settings.llm_api_key:
        raise LLMUnavailable("GEMINI_API_KEY is not set")

    # Imported lazily, not at module scope. `available()` and the cache path must work on a
    # machine that has never installed the SDK — the demo runs from cache, and a missing
    # optional dependency should not stop the API booting.
    from google import genai
    from google.genai import types

    # The SDK logs a WARNING about automatic function calling on every single
    # `generate_content`, advising Chat.send_message instead. We pass no tools, so it does
    # not apply to us — and left alone it puts one misleading warning in the worker log per
    # extracted field, which is how a real warning gets missed.
    logging.getLogger("google_genai.models").setLevel(logging.ERROR)

    client = genai.Client(
        api_key=settings.llm_api_key,
        # Seconds on our side, milliseconds on the SDK's.
        http_options=types.HttpOptions(timeout=settings.llm_timeout_seconds * 1000),
    )

    config = types.GenerateContentConfig(
        system_instruction=(
            system or "You extract structured data from Indian government project reports."),
        temperature=temperature,
        max_output_tokens=max_tokens,
    )
    # Sent only when configured, because the parameter is Gemini-3-only: the 2.5 family
    # rejects the request outright with 400 INVALID_ARGUMENT rather than ignoring it.
    if settings.llm_thinking_level:
        config.thinking_config = types.ThinkingConfig(
            thinking_level=settings.llm_thinking_level)

    resp = client.models.generate_content(
        model=settings.llm_model, contents=prompt, config=config)

    text = resp.text or ""
    if not text.strip():
        # Gemini returns an empty candidate when a safety filter or a token ceiling stops it.
        # Storing that would poison the cache with a blank answer that never retries, and a
        # caller would read it as "the model found nothing" rather than "the model did not
        # answer". Raise instead; callers already degrade on LLMUnavailable.
        cands = getattr(resp, "candidates", None) or [None]
        reason = getattr(cands[0], "finish_reason", None)
        raise LLMUnavailable(
            f"Gemini returned no text (finish_reason={reason}). If this is MAX_TOKENS, the "
            f"thinking budget consumed the output allowance — raise max_tokens or lower "
            f"LLM_THINKING_LEVEL.")

    USAGE["calls"] += 1
    # Every SDK names these fields differently, and any of them can be absent on a cached
    # or filtered response.
    usage = getattr(resp, "usage_metadata", None)
    if usage is not None:
        USAGE["input_tokens"] += getattr(usage, "prompt_token_count", 0) or 0
        # Thinking tokens are billed as output and are NOT included in
        # `candidates_token_count`. Counting only the visible answer would under-report what
        # a document actually cost, which is the one number this counter exists to give.
        USAGE["output_tokens"] += ((getattr(usage, "candidates_token_count", 0) or 0)
                                   + (getattr(usage, "thoughts_token_count", 0) or 0))

    _store(key, prompt, text)
    return text


def reset_usage() -> None:
    """Zero the counter at the start of a document, so what is stored against that document
    is what that document actually cost."""
    for k in USAGE:
        USAGE[k] = 0


def available() -> bool:
    settings = get_settings()
    return bool(settings.llm_api_key) or settings.demo_mode
