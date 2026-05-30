import os

import httpx

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openrouter/free"


class OpenRouterError(Exception):
    pass


async def generate(system_prompt: str, user_prompt: str) -> tuple[str, int]:
    if not OPENROUTER_API_KEY:
        raise OpenRouterError(
            "OPENROUTER_API_KEY environment variable not set"
        )

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise OpenRouterError(
                f"OpenRouter API error {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            raise OpenRouterError(
                f"OpenRouter request failed: {e}"
            ) from e

    data = response.json()
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise OpenRouterError(
            f"Unexpected OpenRouter response format: {data}"
        ) from e

    if text is None or not text.strip():
        raise OpenRouterError(
            f"OpenRouter returned empty/null content. Full response: {data}"
        )

    return text, 0
