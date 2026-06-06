"""Settings loaded once from the environment at import time.

Anything used by handler code in a hot path should live here so the read happens
once, not on every request. Anything that operators might want to change
without a redeploy is read fresh from the environment in the relevant module
(e.g. provider API keys, BIBLE_API_URL).
"""

import os
from dataclasses import dataclass


def _parse_provider_order(raw: str) -> list[str]:
    items = [p.strip() for p in raw.split(",") if p.strip()]
    return items or ["cerebras", "groq", "cloudflare", "openrouter", "cohere", "together"]


@dataclass(frozen=True)
class Settings:
    provider_order: list[str]
    max_retries: int
    max_concurrency: int
    client_secret: str | None


def load() -> Settings:
    return Settings(
        provider_order=_parse_provider_order(
            os.getenv("LOOKUP_PROVIDER_ORDER", "gemini,openrouter,groq")
        ),
        max_retries=int(os.getenv("LOOKUP_MAX_RETRIES", "3")),
        max_concurrency=int(os.getenv("LOOKUP_MAX_CONCURRENCY", "8")),
        client_secret=os.getenv("LOOKUP_CLIENT_SECRET") or None,
    )


SETTINGS = load()
