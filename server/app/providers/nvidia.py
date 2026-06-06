import os

import httpx

NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_MODEL = "nvidia/nvidia-nemotron-nano-9b-v2"

NAME = "nvidia"
MODEL = NVIDIA_MODEL


class NvidiaError(Exception):
    pass


async def generate(system_prompt: str, user_prompt: str, *, timeout: float = 60) -> str:
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise NvidiaError("NVIDIA_API_KEY not set")

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(
                NVIDIA_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                # Nemotron is a reasoning model: it spends a "thinking" budget
                # before the answer. We keep that budget bounded and leave ample
                # max_tokens so the JSON selection still lands in `content` (the
                # reasoning goes to a separate `reasoning_content` we ignore).
                json={
                    "model": NVIDIA_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.6,
                    "top_p": 0.95,
                    "max_tokens": 4096,
                    "min_thinking_tokens": 256,
                    "max_thinking_tokens": 1024,
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise NvidiaError(
                f"NVIDIA API error {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            raise NvidiaError(f"NVIDIA request failed: {e}") from e

    data = response.json()
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise NvidiaError(f"Unexpected NVIDIA response format: {data}") from e

    if not text or not text.strip():
        raise NvidiaError(f"NVIDIA returned empty content: {data}")

    return text
