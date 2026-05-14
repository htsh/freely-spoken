import os

import httpx

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"


class GroqError(Exception):
    pass


async def generate(system_prompt: str, user_prompt: str) -> tuple[str, int]:
    if not GROQ_API_KEY:
        raise GroqError("GROQ_API_KEY environment variable not set")

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
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
        raise GroqError(
            f"Unexpected Groq response format: {data}"
        ) from e

    return text, 0
