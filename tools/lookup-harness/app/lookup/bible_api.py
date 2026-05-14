"""bible-api.com client.

Spec: https://bible-api.com/

GET {base}/{ref}?translation={id}
  -> {
       "reference": "John 3:16",
       "verses": [{"book_id", "book_name", "chapter", "verse", "text"}],
       "text": "<joined passage>",
       "translation_id": "web",
       "translation_name": "World English Bible",
       "translation_note": "Public Domain"
     }

The public host is rate-limited to 15 req / 30s per IP and is described as a
hobby service. We cache successful fetches per-process keyed by (ref, translation)
so repeat runs over the same fixtures are free. Errors are surfaced soft —
callers attach them to a single Reference rather than failing the lookup.

Both the host and translation are env-configurable so swapping to a self-hosted
copy on a VPS later is one variable change.
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
    """Fetch the canonical text for a reference like "John 3:16".

    Raises BibleApiError on any failure (network, HTTP, malformed payload).
    Successful results are cached per-process by (ref, translation).
    """
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
        # API includes leading/trailing newlines and per-verse \n separators
        # we want a single clean paragraph for display.
        text=" ".join(text.split()).strip(),
        translation_id=data.get("translation_id", translation),
        translation_name=data.get("translation_name", translation),
    )
    _cache[cache_key] = verse
    return verse
