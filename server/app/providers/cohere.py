import os

import httpx

COHERE_URL = "https://api.cohere.com/v2/chat"
COHERE_MODEL = "command-r-08-2024"

NAME = "cohere"
MODEL = COHERE_MODEL


class CohereError(Exception):
    pass


async def generate(system_prompt: str, user_prompt: str) -> str:
    """One-shot Cohere v2 chat call. Retries and fallback are handled by llm_runner."""
    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        raise CohereError("COHERE_API_KEY not set")

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(
                COHERE_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": COHERE_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise CohereError(
                f"Cohere API error {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            raise CohereError(f"Cohere request failed: {e}") from e

    data = response.json()
    # Cohere v2 returns message.content as a list of typed blocks; concatenate
    # the text blocks (normally just one) into a single string.
    try:
        blocks = data["message"]["content"]
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    except (KeyError, IndexError, TypeError) as e:
        raise CohereError(f"Unexpected Cohere response format: {data}") from e

    if not text or not text.strip():
        raise CohereError(f"Cohere returned empty content: {data}")

    return text
