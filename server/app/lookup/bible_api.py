"""bible-api.com client.

Spec: https://bible-api.com/

Env-configurable so swapping to a self-hosted mirror is a config-only change.
Successful fetches are cached per-process keyed by (ref, translation); the
cache survives until the worker is replaced. The public host is rate-limited
to ~15 req / 30s per IP, so the cache materially reduces 429s under repeat
lookups.
"""

import os
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote

import httpx

DEFAULT_BASE_URL = "https://bible-api.com"
DEFAULT_TRANSLATION = "web"
_TIMEOUT_SECONDS = 10

_cache: dict[tuple[str, str], "Verse"] = {}


@dataclass
class Verse:
    reference: str
    text: str
    translation_id: str
    translation_name: str


class BibleApiError(Exception):
    pass


def _base_url() -> str:
    return os.getenv("BIBLE_API_URL", DEFAULT_BASE_URL).rstrip("/")


def default_translation() -> str:
    return os.getenv("BIBLE_TRANSLATION", DEFAULT_TRANSLATION)


async def fetch_verse(ref: str, translation: Optional[str] = None) -> Verse:
    translation = translation or default_translation()
    cache_key = (ref, translation)
    if cache_key in _cache:
        return _cache[cache_key]

    url = f"{_base_url()}/{quote(ref)}"
    params = {"translation": translation}

    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise BibleApiError(
                f"bible-api error {e.response.status_code} for {ref!r}"
            ) from e
        except httpx.RequestError as e:
            raise BibleApiError(
                f"bible-api request failed for {ref!r}: {e}"
            ) from e

    try:
        data = response.json()
    except ValueError as e:
        raise BibleApiError(f"bible-api returned non-JSON for {ref!r}") from e

    text = data.get("text")
    if not text or not text.strip():
        raise BibleApiError(
            f"bible-api returned empty text for {ref!r}: {data!r}"
        )

    verse = Verse(
        reference=data.get("reference", ref),
        text=" ".join(text.split()).strip(),
        translation_id=data.get("translation_id", translation),
        translation_name=data.get("translation_name", translation),
    )
    _cache[cache_key] = verse
    return verse
