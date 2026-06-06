#!/usr/bin/env python3
"""Smoke-test the HuggingFace last-resort provider IN ISOLATION.

HuggingFace sits at the end of the chain and is never reached under normal load,
so a broken key / renamed model / changed endpoint would go unnoticed until the
one moment you needed the backstop. This script calls the adapter directly
(bypassing the provider chain) so you can confirm the insurance is in force —
run it after setup, and on a schedule (e.g. weekly cron) to catch silent rot.

Usage (from server/):
    .venv/bin/python scripts/hf_smoke.py

Reads HF_TOKEN / HF_MODEL from the environment or a local .env. Exits 0 on a
usable response, non-zero (with a reason) otherwise — so cron/CI can alert.
"""

import asyncio
import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

# Import after load_dotenv so HF_MODEL is picked up.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.providers import huggingface  # noqa: E402

# A representative selection-style prompt: the real backend only asks the model
# to choose and emit small JSON, never to author canonical text.
_SYSTEM = "You select. Reply with only a JSON object."
_USER = 'Choose one id. Candidates: ["a","b","c"]. Reply: {"id": "<one of them>"}'


async def main() -> int:
    if not os.getenv("HF_TOKEN"):
        print("FAIL: HF_TOKEN not set (put it in server/.env or the environment)", file=sys.stderr)
        return 2

    model = os.getenv("HF_MODEL", huggingface.DEFAULT_MODEL)
    print(f"Hitting HuggingFace router with model: {model}")

    start = time.monotonic()
    try:
        text = await huggingface.generate(_SYSTEM, _USER, timeout=30)
    except huggingface.HuggingFaceError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1

    elapsed_ms = (time.monotonic() - start) * 1000
    print(f"OK ({elapsed_ms:.0f}ms). Response:\n{text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
