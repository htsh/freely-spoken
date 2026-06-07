"""HuggingFace router provider — the paid last-resort backstop.

Unlike the other providers (free tiers that rate-limit), this one bills against
HuggingFace Inference Providers credit. It sits at the very end of the chain and
is only reached when every free provider ahead of it has failed, so under normal
load it is never called. That makes it cheap insurance: the credit is spent only
on the rare requests that would otherwise fail outright.

The router is OpenAI-compatible, so this is the same shape as the other adapters.
The model carries a `:fireworks-ai` suffix that routes to a specific upstream
provider; override it with HF_MODEL without a code change (useful if the default
ever fumbles the JSON selection — there is no provider behind this one to catch
it).
"""

import os

import httpx

HF_URL = "https://router.huggingface.co/v1/chat/completions"
# DeepSeek-V4-Flash: chosen as the backstop for sharper selection on hard
# emotional inputs and fewer spurious refusals than smaller models, while still
# cheap at tail volume. Override with HF_MODEL. The backend LLM only selects a
# canonical id from a shortlist; it never authors text.
DEFAULT_MODEL = "deepseek-ai/DeepSeek-V4-Flash:fireworks-ai"

NAME = "huggingface"
MODEL = os.getenv("HF_MODEL", DEFAULT_MODEL)


class HuggingFaceError(Exception):
    pass


async def generate(system_prompt: str, user_prompt: str, *, timeout: float = 60) -> str:
    api_key = os.getenv("HF_TOKEN")
    if not api_key:
        raise HuggingFaceError("HF_TOKEN not set")

    model = os.getenv("HF_MODEL", DEFAULT_MODEL)

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(
                HF_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.3,
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HuggingFaceError(
                f"HuggingFace API error {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            raise HuggingFaceError(f"HuggingFace request failed: {e}") from e

    data = response.json()
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise HuggingFaceError(f"Unexpected HuggingFace response format: {data}") from e

    if not text or not text.strip():
        raise HuggingFaceError(f"HuggingFace returned empty content: {data}")

    return text
