"""Walk the configured provider chain and run a prompt with retries + fallback.

Behavior:
- Try providers in the configured order.
- On HTTP 429: immediately move to the next provider (no retry on this one).
- On 5xx / timeout / connect error: retry with jittered backoff up to max_retries
  on the same provider; if it still fails, move to the next provider.
- If every provider has been exhausted, raise AllProvidersFailedError with the
  last error attached.

Returns:
- text   — the raw LLM string
- name   — the provider that produced it ("gemini" / "openrouter" / "groq")
- model  — the concrete model id
- retry_count — number of retries performed *inside the winning provider*
- fallback_used — true if a non-primary provider was used
"""

import asyncio
import logging
import random
from dataclasses import dataclass
from typing import Awaitable, Callable

import httpx

from app.config import SETTINGS
from app.providers import cloudflare, gemini, groq, openrouter

logger = logging.getLogger(__name__)

_BASE_DELAY = 1.0

PROVIDERS: dict[str, tuple[str, Callable[[str, str], Awaitable[str]]]] = {
    gemini.NAME: (gemini.MODEL, gemini.generate),
    openrouter.NAME: (openrouter.MODEL, openrouter.generate),
    groq.NAME: (groq.MODEL, groq.generate),
    cloudflare.NAME: (cloudflare.MODEL, cloudflare.generate),
}

_ERRORS = (cloudflare.CloudflareError, gemini.GeminiError, openrouter.OpenRouterError, groq.GroqError)


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str
    retry_count: int
    fallback_used: bool


class AllProvidersFailedError(Exception):
    def __init__(self, last_error: Exception | None):
        super().__init__(
            f"All providers exhausted. Last error: {last_error!r}"
        )
        self.last_error = last_error


def _status_code(error: Exception) -> int | None:
    cause = getattr(error, "__cause__", None)
    if isinstance(cause, httpx.HTTPStatusError):
        return cause.response.status_code
    return None


def _is_rate_limit(error: Exception) -> bool:
    return _status_code(error) == 429


def _is_transient(error: Exception) -> bool:
    code = _status_code(error)
    if code in (500, 502, 503, 504):
        return True
    cause = getattr(error, "__cause__", None)
    return isinstance(cause, (httpx.TimeoutException, httpx.ConnectError))


async def run(system_prompt: str, user_prompt: str) -> LLMResult:
    order = SETTINGS.provider_order
    max_retries = SETTINGS.max_retries
    primary = order[0] if order else None
    last_error: Exception | None = None

    for name in order:
        if name not in PROVIDERS:
            logger.warning("unknown_provider_in_order", extra={"provider": name})
            continue

        model, generate = PROVIDERS[name]

        # Try this provider with bounded retries for transient errors.
        for attempt in range(max_retries):
            try:
                text = await generate(system_prompt, user_prompt)
                return LLMResult(
                    text=text,
                    provider=name,
                    model=model,
                    retry_count=attempt,
                    fallback_used=(name != primary),
                )
            except _ERRORS as e:
                last_error = e
                if _is_rate_limit(e):
                    # immediate fallback — do not retry on this provider
                    break
                if not _is_transient(e):
                    # final non-retryable error on this provider; move on
                    break
                if attempt == max_retries - 1:
                    # exhausted this provider's retry budget
                    break
                delay = _BASE_DELAY * (2**attempt) + random.uniform(0, 1)
                await asyncio.sleep(delay)

    raise AllProvidersFailedError(last_error)
