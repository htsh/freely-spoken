import os

import httpx

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"

NAME = "groq"
MODEL = GROQ_MODEL


class GroqError(Exception):
    pass


async def generate(system_prompt: str, user_prompt: str) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise GroqError("GROQ_API_KEY not set")

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise GroqError(
                f"Groq API error {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            raise GroqError(f"Groq request failed: {e}") from e

    data = response.json()
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise GroqError(f"Unexpected Groq response format: {data}") from e

    if not text or not text.strip():
        raise GroqError(f"Groq returned empty content: {data}")

    return text
