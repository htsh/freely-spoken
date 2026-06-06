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
from typing import Any, Awaitable, Callable

import httpx

from app.config import SETTINGS
from app.providers import cerebras, cloudflare, cohere, gemini, groq, huggingface, mistral, nvidia, openrouter, together

logger = logging.getLogger(__name__)

_BASE_DELAY = 1.0

PROVIDERS: dict[str, tuple[str, Callable[[str, str], Awaitable[str]]]] = {
    gemini.NAME: (gemini.MODEL, gemini.generate),
    openrouter.NAME: (openrouter.MODEL, openrouter.generate),
    groq.NAME: (groq.MODEL, groq.generate),
    cloudflare.NAME: (cloudflare.MODEL, cloudflare.generate),
    together.NAME: (together.MODEL, together.generate),
    cerebras.NAME: (cerebras.MODEL, cerebras.generate),
    cohere.NAME: (cohere.MODEL, cohere.generate),
    mistral.NAME: (mistral.MODEL, mistral.generate),
    nvidia.NAME: (nvidia.MODEL, nvidia.generate),
    huggingface.NAME: (huggingface.MODEL, huggingface.generate),
}

_ERRORS = (cerebras.CerebrasError, cloudflare.CloudflareError, cohere.CohereError, gemini.GeminiError, huggingface.HuggingFaceError, mistral.MistralError, nvidia.NvidiaError, openrouter.OpenRouterError, groq.GroqError, together.TogetherError)


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str
    retry_count: int
    fallback_used: bool
    parsed: Any = None  # value returned by an optional validate() callback
    providers_attempted: list[str] = None  # ordered list of providers tried
    provider_errors: dict[str, str] = None  # provider -> failure reason for each skip

    def __post_init__(self):
        if self.providers_attempted is None:
            self.providers_attempted = []
        if self.provider_errors is None:
            self.provider_errors = {}


class AllProvidersFailedError(Exception):
    def __init__(
        self,
        last_error: Exception | None,
        *,
        providers_attempted: list[str] | None = None,
        provider_errors: dict[str, str] | None = None,
    ):
        super().__init__(
            f"All providers exhausted. Last error: {last_error!r}"
        )
        self.last_error = last_error
        # Operational context for alerting — provider names and failure reasons
        # only. Never the prompt/body text (see the privacy allowlist).
        self.providers_attempted = providers_attempted or []
        self.provider_errors = provider_errors or {}


class OutputValidationError(Exception):
    """Raised by a validate() callback when a provider's output is structurally
    unusable (e.g. malformed JSON, an out-of-set id).

    The runner treats this like a provider failure: it does NOT retry the same
    model (re-prompting rarely fixes structural errors and only adds latency) and
    falls through to the next provider. If every provider's output fails
    validation, AllProvidersFailedError is raised with the last one attached.
    Adapters subclass this so their existing error types trigger fallthrough.
    """


def _status_code(error: Exception) -> int | None:
    cause = getattr(error, "__cause__", None)
    if isinstance(cause, httpx.HTTPStatusError):
        return cause.response.status_code
    return None


def _is_rate_limit(error: Exception) -> bool:
    return _status_code(error) == 429


def _is_timeout(error: Exception) -> bool:
    cause = getattr(error, "__cause__", None)
    return isinstance(cause, httpx.TimeoutException)


def _is_transient(error: Exception) -> bool:
    # Worth a same-provider retry: a server hiccup or a transient connect blip.
    # Timeouts are deliberately excluded — see the runner loop.
    code = _status_code(error)
    if code in (500, 502, 503, 504):
        return True
    cause = getattr(error, "__cause__", None)
    return isinstance(cause, httpx.ConnectError)


def _effective_order(order: list[str], fast_tier: list[str]) -> list[str]:
    """Build this request's provider order.

    Members of `fast_tier` (in any position in `order`) are shuffled to the
    front; everything else keeps its original relative order as a fixed
    last-resort tail. With an empty `fast_tier` the static order is returned
    unchanged. Shuffling per request spreads concurrent load across the fast
    providers so they rate-limit less and the chain reaches the slow tail less
    often.
    """
    if not fast_tier:
        return list(order)
    fast = [p for p in order if p in fast_tier]
    rest = [p for p in order if p not in fast_tier]
    random.shuffle(fast)
    return fast + rest


def _error_reason(error: Exception) -> str:
    code = _status_code(error)
    if code == 429:
        return "rate_limited"
    if code in (500, 502, 503, 504):
        return f"http_{code}"
    cause = getattr(error, "__cause__", None)
    if isinstance(cause, httpx.TimeoutException):
        return "timeout"
    if isinstance(cause, httpx.ConnectError):
        return "connect_error"
    if isinstance(error, OutputValidationError):
        return "bad_output"
    return f"error({type(error).__name__})"


async def run(
    system_prompt: str,
    user_prompt: str,
    *,
    validate: Callable[[str], Any] | None = None,
) -> LLMResult:
    """Run the prompt through the provider chain.

    If `validate` is given it is called with each provider's raw text. Returning
    a value accepts that provider (the value is exposed as LLMResult.parsed);
    raising OutputValidationError rejects the output and falls through to the
    next provider, so one provider's malformed response no longer fails the whole
    request when another provider can produce something usable.
    """
    order = _effective_order(SETTINGS.provider_order, SETTINGS.fast_tier)
    max_retries = SETTINGS.max_retries
    primary = order[0] if order else None
    last_error: Exception | None = None
    providers_attempted: list[str] = []
    provider_errors: dict[str, str] = {}

    for name in order:
        if name not in PROVIDERS:
            logger.warning("unknown_provider_in_order", extra={"provider": name})
            continue

        providers_attempted.append(name)
        model, generate = PROVIDERS[name]
        timeout = SETTINGS.provider_timeouts.get(name, SETTINGS.default_timeout)
        this_error: Exception | None = None

        # Try this provider with bounded retries for transient errors.
        for attempt in range(max_retries):
            try:
                text = await generate(system_prompt, user_prompt, timeout=timeout)
            except _ERRORS as e:
                last_error = e
                this_error = e
                if _is_rate_limit(e) or _is_timeout(e):
                    # 429 or a too-slow provider: retrying the same one won't help
                    # and only burns the client's overall budget. Fall through to
                    # the next provider immediately.
                    break
                if not _is_transient(e):
                    # final non-retryable error on this provider; move on
                    break
                if attempt == max_retries - 1:
                    # exhausted this provider's retry budget
                    break
                delay = _BASE_DELAY * (2**attempt) + random.uniform(0, 1)
                await asyncio.sleep(delay)
                continue

            # Provider returned text. If a validator is supplied, the output must
            # also be usable; unusable output falls through to the next provider
            # rather than failing the request outright.
            if validate is not None:
                try:
                    parsed = validate(text)
                except OutputValidationError as e:
                    last_error = e
                    this_error = e
                    break
            else:
                parsed = None

            return LLMResult(
                text=text,
                provider=name,
                model=model,
                retry_count=attempt,
                fallback_used=(name != primary),
                parsed=parsed,
                providers_attempted=providers_attempted,
                provider_errors=provider_errors,
            )

        if this_error is not None:
            provider_errors[name] = _error_reason(this_error)

    raise AllProvidersFailedError(
        last_error,
        providers_attempted=providers_attempted,
        provider_errors=provider_errors,
    )
