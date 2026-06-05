import os

import httpx

CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
CEREBRAS_MODEL = "gpt-oss-120b"

NAME = "cerebras"
MODEL = CEREBRAS_MODEL


class CerebrasError(Exception):
    pass


async def generate(system_prompt: str, user_prompt: str) -> str:
    """One-shot Cerebras call. Retries and fallback are handled by llm_runner."""
    api_key = os.getenv("CEREBRAS_API_KEY")
    if not api_key:
        raise CerebrasError("CEREBRAS_API_KEY not set")

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(
                CEREBRAS_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": CEREBRAS_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise CerebrasError(
                f"Cerebras API error {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            raise CerebrasError(f"Cerebras request failed: {e}") from e

    data = response.json()
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise CerebrasError(
            f"Unexpected Cerebras response format: {data}"
        ) from e

    if not text or not text.strip():
        raise CerebrasError(f"Cerebras returned empty content: {data}")

    return text
