import os

import httpx

GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

NAME = "gemini"
MODEL = GEMINI_MODEL


class GeminiError(Exception):
    pass


async def generate(system_prompt: str, user_prompt: str) -> str:
    """One-shot Gemini call. Retries and fallback are handled by llm_runner."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise GeminiError("GEMINI_API_KEY not set")

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(
                GEMINI_URL,
                params={"key": api_key},
                json={
                    "system_instruction": {"parts": [{"text": system_prompt}]},
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
            raise GeminiError(
                f"Gemini API error {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            raise GeminiError(f"Gemini request failed: {e}") from e

    data = response.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise GeminiError(f"Unexpected Gemini response format: {data}") from e

    if not text or not text.strip():
        raise GeminiError(f"Gemini returned empty content: {data}")

    return text
