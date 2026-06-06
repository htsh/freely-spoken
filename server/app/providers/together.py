import os

import httpx

TOGETHER_URL = "https://api.together.xyz/v1/chat/completions"
TOGETHER_MODEL = "openai/gpt-oss-20b"

NAME = "together"
MODEL = TOGETHER_MODEL


class TogetherError(Exception):
    pass


async def generate(system_prompt: str, user_prompt: str, *, timeout: float = 60) -> str:
    """One-shot Together AI call. Retries and fallback are handled by llm_runner."""
    api_key = os.getenv("TOGETHER_API_KEY")
    if not api_key:
        raise TogetherError("TOGETHER_API_KEY not set")

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(
                TOGETHER_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": TOGETHER_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise TogetherError(
                f"Together API error {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            raise TogetherError(f"Together request failed: {e}") from e

    data = response.json()
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise TogetherError(
            f"Unexpected Together response format: {data}"
        ) from e

    if not text or not text.strip():
        raise TogetherError(f"Together returned empty content: {data}")

    return text
