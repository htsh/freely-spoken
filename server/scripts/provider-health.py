#!/usr/bin/env python3
"""Probe every configured LLM provider with one tiny prompt and report health.

Run inside the deploy container so it sees the real .env keys:

    docker run --rm --env-file .env \
      -v "$PWD/scripts:/app/scripts" \
      mic-check-lookup:latest python scripts/provider-health.py

For each provider it prints OK + latency + a snippet of the reply, or the error.
Use this to decide LOOKUP_PROVIDER_ORDER: put fast, reliable providers first.
It makes one real call per provider, so it costs a few tokens but no more.
"""

from __future__ import annotations

import asyncio
import time

from app.providers import cerebras, cloudflare, cohere, gemini, groq, openrouter, together

_SYSTEM = "You are a terse assistant. Reply with valid minimal JSON only."
_USER = 'Return exactly: {"ok": true}'

_PROVIDERS = [cerebras, cloudflare, cohere, gemini, groq, openrouter, together]


async def _probe(mod) -> tuple[str, str, float, str]:
    started = time.perf_counter()
    try:
        text = await mod.generate(_SYSTEM, _USER)
        ms = (time.perf_counter() - started) * 1000
        snippet = " ".join(text.split())[:60]
        return mod.NAME, "OK", ms, snippet
    except Exception as e:  # provider-specific error types all subclass Exception
        ms = (time.perf_counter() - started) * 1000
        return mod.NAME, "FAIL", ms, f"{type(e).__name__}: {e}"[:120]


async def main() -> None:
    results = await asyncio.gather(*(_probe(m) for m in _PROVIDERS))
    print(f"{'provider':12} {'status':6} {'ms':>8}  detail")
    print("-" * 70)
    for name, status, ms, detail in sorted(results, key=lambda r: (r[1] != "OK", r[2])):
        print(f"{name:12} {status:6} {ms:8.0f}  {detail}")


if __name__ == "__main__":
    asyncio.run(main())
