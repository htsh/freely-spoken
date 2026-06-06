"""Settings loaded once from the environment at import time.

Anything used by handler code in a hot path should live here so the read happens
once, not on every request. Anything that operators might want to change
without a redeploy is read fresh from the environment in the relevant module
(e.g. provider API keys, BIBLE_API_URL).
"""

import os
from dataclasses import dataclass


_DEFAULT_ORDER = ["groq", "cerebras", "mistral", "nvidia", "cloudflare", "openrouter", "cohere", "together"]


def _parse_provider_order(raw: str) -> list[str]:
    items = [p.strip() for p in raw.split(",") if p.strip()]
    return items or list(_DEFAULT_ORDER)


def _parse_fast_tier(raw: str) -> list[str]:
    """Providers eligible for per-request shuffle. Empty disables rotation."""
    return [p.strip() for p in raw.split(",") if p.strip()]


def _parse_provider_timeouts(raw: str) -> dict[str, float]:
    """Parse "openrouter:15,cohere:20" into {provider: seconds}."""
    out: dict[str, float] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        name, _, val = pair.partition(":")
        try:
            out[name.strip()] = float(val.strip())
        except ValueError:
            continue
    return out


@dataclass(frozen=True)
class Settings:
    provider_order: list[str]
    fast_tier: list[str]
    provider_timeouts: dict[str, float]
    default_timeout: float
    max_retries: int
    max_concurrency: int
    client_secret: str | None


def load() -> Settings:
    return Settings(
        provider_order=_parse_provider_order(os.getenv("LOOKUP_PROVIDER_ORDER", "")),
        fast_tier=_parse_fast_tier(
            os.getenv("LOOKUP_FAST_TIER", "groq,cerebras,mistral")
        ),
        provider_timeouts=_parse_provider_timeouts(
            os.getenv("LOOKUP_PROVIDER_TIMEOUTS", "nvidia:15,openrouter:15,cohere:20,cloudflare:15,together:15")
        ),
        default_timeout=float(os.getenv("LOOKUP_DEFAULT_TIMEOUT", "60")),
        max_retries=int(os.getenv("LOOKUP_MAX_RETRIES", "3")),
        max_concurrency=int(os.getenv("LOOKUP_MAX_CONCURRENCY", "8")),
        client_secret=os.getenv("LOOKUP_CLIENT_SECRET") or None,
    )


SETTINGS = load()
