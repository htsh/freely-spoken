#!/usr/bin/env python3
"""Task 7.2 live selection review — run the REAL production Dhammapada adapter
over the test fixtures, swapping only the model call to Fireworks.

Everything else is the shipping code path: app.lookup.dhammapada's shortlist,
compact index, selector prompt, ID/quotation validation, crisis filter, and
local text enrichment. Only `run_llm` is monkeypatched to call a Fireworks
OpenAI-compatible chat endpoint, so this exercises selection quality without
needing a runtime-provider key.

NOTE: Fireworks (kimi-k2p6) is a stand-in, not the runtime provider (Gemini
Flash). A confirming run on Gemini is still wanted before release. This review
is about whether the prompt + catalog support good, well-toned selections.

Run:  server/.venv/bin/python tools/dhammapada-labeling/review/live_lookup_review.py
Env:  FIREWORKS_API_KEY
"""
from __future__ import annotations
import asyncio
import json
import os
import sys
import textwrap
import urllib.request

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server"))

import app.lookup.dhammapada as d  # noqa: E402
from app.llm_runner import LLMResult  # noqa: E402
from app.lookup.base import LookupRequest  # noqa: E402

MODEL = "accounts/fireworks/models/kimi-k2p6"
FIXTURES = os.path.join(REPO, "server", "tests", "fixtures", "lookup_inputs.json")


def _fireworks(system: str, user: str) -> str:
    body = json.dumps({
        "model": MODEL,
        "temperature": 0.3,
        "max_tokens": 1200,
        # kimi-k2p6 reasons in prose first; force a JSON-only object so the
        # selector output is parseable (a runtime selector would use the same
        # constrained-decoding switch — adapter-plan.md §4.1).
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }).encode()
    req = urllib.request.Request(
        "https://api.fireworks.ai/inference/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {os.environ['FIREWORKS_API_KEY']}",
            "Content-Type": "application/json",
            "User-Agent": "dhammapada-review/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        out = json.load(resp)
    return out["choices"][0]["message"]["content"]


async def _run_llm(system: str, user: str) -> LLMResult:
    text = await asyncio.to_thread(_fireworks, system, user)
    return LLMResult(text=text, provider="fireworks", model="kimi-k2p6",
                     retry_count=0, fallback_used=False)


def _show(tag: str, ref) -> None:
    wrapped = textwrap.fill(ref.text, width=88, initial_indent="      ",
                            subsequent_indent="      ")
    print(f"  {tag}: {ref.ref}")
    print(f"      reason: {ref.shortReason}")
    print(wrapped)


async def main() -> None:
    d.run_llm = _run_llm  # swap only the model call
    fixtures = json.load(open(FIXTURES))["fixtures"]

    # run every fixture non-crisis; also re-run the safety-relevant ones with crisis_flag
    crisis_names = {"grief", "shame", "panic"}

    for fx in fixtures:
        for crisis in ([False, True] if fx["name"] in crisis_names else [False]):
            req = LookupRequest(
                anonymized_text=fx["anonymizedText"], sentiment=fx["sentiment"],
                emotions=fx["emotions"], confidence=fx["confidence"], crisis_flag=crisis,
            )
            banner = f"=== {fx['name']}{' [CRISIS]' if crisis else ''} ==="
            print("\n" + banner)
            print("  situation:", fx["anonymizedText"])
            print("  emotions:", ", ".join(fx["emotions"]), "| sentiment:", fx["sentiment"])
            try:
                res = await d.DhammapadaAdapter().select(req)
            except d.LookupUnavailableError as e:
                print("  -> lookup_unavailable:", e)
                continue
            except d.DhammapadaAdapterError as e:
                print("  -> ADAPTER ERROR:", str(e)[:160])
                continue
            _show("PRIMARY", res.primary)
            for i, a in enumerate(res.alternates, 1):
                _show(f"alt{i}", a)


if __name__ == "__main__":
    asyncio.run(main())
