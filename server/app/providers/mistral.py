import os

import httpx

MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MISTRAL_MODEL = "mistral-small-latest"

NAME = "mistral"
MODEL = MISTRAL_MODEL


class MistralError(Exception):
    pass


async def generate(system_prompt: str, user_prompt: str, *, timeout: float = 60) -> str:
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise MistralError("MISTRAL_API_KEY not set")

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(
                MISTRAL_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MISTRAL_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise MistralError(
                f"Mistral API error {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            raise MistralError(f"Mistral request failed: {e}") from e

    data = response.json()
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise MistralError(f"Unexpected Mistral response format: {data}") from e

    if not text or not text.strip():
        raise MistralError(f"Mistral returned empty content: {data}")

    return text
