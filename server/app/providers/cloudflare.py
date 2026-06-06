import os

import httpx

CLOUDFLARE_MODEL = "@cf/meta/llama-3.1-8b-instruct"

NAME = "cloudflare"
MODEL = CLOUDFLARE_MODEL


class CloudflareError(Exception):
    pass


async def generate(system_prompt: str, user_prompt: str, *, timeout: float = 60) -> str:
    """One-shot Cloudflare Workers AI call. Retries and fallback are handled by llm_runner."""
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    api_token = os.getenv("CLOUDFLARE_API_TOKEN")
    if not account_id:
        raise CloudflareError("CLOUDFLARE_ACCOUNT_ID not set")
    if not api_token:
        raise CloudflareError("CLOUDFLARE_API_TOKEN not set")

    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
        f"/ai/run/{CLOUDFLARE_MODEL}"
    )

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise CloudflareError(
                f"Cloudflare API error {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            raise CloudflareError(f"Cloudflare request failed: {e}") from e

    data = response.json()
    if not data.get("success"):
        errors = data.get("errors", [])
        raise CloudflareError(f"Cloudflare API returned errors: {errors}")

    try:
        text = data["result"]["response"]
    except (KeyError, IndexError) as e:
        raise CloudflareError(
            f"Unexpected Cloudflare response format: {data}"
        ) from e

    if not text or not text.strip():
        raise CloudflareError(f"Cloudflare returned empty content: {data}")

    return text
