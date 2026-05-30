import asyncio
import os
import random

import httpx

GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
_MAX_RETRIES = 3
_BASE_DELAY = 1.0


class GeminiError(Exception):
    pass


def _is_retryable(error: GeminiError) -> bool:
    cause = getattr(error, "__cause__", None)
    if isinstance(cause, httpx.HTTPStatusError):
        return cause.response.status_code in _RETRYABLE_STATUS_CODES
    if isinstance(cause, (httpx.TimeoutException, httpx.ConnectError)):
        return True
    return False


async def _generate_once(
    system_prompt: str, user_prompt: str
) -> str:
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise GeminiError("GEMINI_API_KEY environment variable not set")

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(
                GEMINI_URL,
                params={"key": gemini_api_key},
                json={
                    "system_instruction": {
                        "parts": [{"text": system_prompt}]
                    },
                    "contents": [
                        {"role": "user", "parts": [{"text": user_prompt}]}
                    ],
                    "generationConfig": {
                        "responseMimeType": "application/json",
                    },
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise GeminiError(
                    "Rate limited by Gemini API (429)"
                ) from e
            raise GeminiError(
                f"Gemini API error {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            raise GeminiError(f"Gemini request failed: {e}") from e

    data = response.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise GeminiError(
            f"Unexpected Gemini response format: {data}"
        ) from e

    if text is None or not text.strip():
        raise GeminiError(
            f"Gemini returned empty/null content. Full response: {data}"
        )

    return text


async def generate(
    system_prompt: str, user_prompt: str
) -> tuple[str, int]:
    for attempt in range(_MAX_RETRIES):
        try:
            text = await _generate_once(system_prompt, user_prompt)
            return text, attempt
        except GeminiError as e:
            if not _is_retryable(e):
                raise
            if attempt == _MAX_RETRIES - 1:
                raise e

        delay = _BASE_DELAY * (2 ** attempt) + random.uniform(0, 1)
        print(
            f"[gemini] Retry {attempt + 2}/{_MAX_RETRIES} "
            f"after {delay:.1f}s..."
        )
        await asyncio.sleep(delay)

    # Unreachable — every path either returns or raises above.
    raise GeminiError("Unexpected: retry loop exhausted without raising")
