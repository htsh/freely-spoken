#!/usr/bin/env python3
"""Cost + latency smoke test for the HuggingFace last-resort backstop.

Fires N real requests at the HuggingFace router (the paid backstop the lookup
backend falls to only when every free provider fails), reads the *actual* token
usage returned by each response, and computes what those calls cost. Use it to
answer "if the backstop ever takes real traffic, what's my bill?" before you
ship to TestFlight / the App Store.

Self-contained: only needs `httpx` and HF_TOKEN. No app code, so it copies
cleanly to vps1 next to your other load-test script.

    python hf_cost_smoke.py 20
    python hf_cost_smoke.py 30 --in-price 0.10 --out-price 0.50 --concurrency 2

PRICING NOTE: the default $/1M-token rates below are ESTIMATES. Look up the real
numbers for your model on the HuggingFace router / upstream provider and pass
--in-price / --out-price. The token *counts* are measured for real either way,
so once the rates are right the dollar figure is accurate.
"""

import argparse
import asyncio
import os
import statistics
import sys
import time

import httpx

HF_URL = "https://router.huggingface.co/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-20b:fireworks-ai"

# ── ESTIMATES — verify and override with --in-price / --out-price ──────────────
DEFAULT_IN_PRICE = 0.10   # $ per 1M input (prompt) tokens
DEFAULT_OUT_PRICE = 0.50  # $ per 1M output (completion) tokens

# A representative selection prompt: the real backend only asks the model to pick
# canonical ids from a shortlist and emit small JSON — it never authors text. The
# candidate list is sized to roughly match a production lookup so token counts
# (and therefore cost) are realistic.
SYSTEM_PROMPT = (
    "You are a passage selector. From the candidate list, choose the three ids "
    "that best fit the reader's state. Reply with ONLY a JSON object of the form "
    '{"primary": {"id": "..."}, "alternates": [{"id": "..."}, {"id": "..."}]}. '
    "Do not author or quote any passage text. Choose only from the ids shown."
)
_CANDIDATES = "\n".join(
    f'- id "psg-{i:03d}": a short reflection on '
    + ["patience", "loss", "gratitude", "anger", "doubt", "hope", "fear", "rest"][i % 8]
    for i in range(30)
)
USER_PROMPT = (
    "Reader state: anonymized sentiment=anxious, emotions=[restlessness, "
    "self-doubt], confidence=0.62.\n\nCandidates:\n" + _CANDIDATES + "\n\nReturn the JSON."
)


async def _one_call(client, model, token, timeout):
    """Return (ok, latency_ms, prompt_tokens, completion_tokens, error)."""
    start = time.monotonic()
    try:
        resp = await client.post(
            HF_URL,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": USER_PROMPT},
                ],
                "temperature": 0.3,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
    except Exception as e:  # noqa: BLE001 — smoke test wants every failure reason
        return (False, (time.monotonic() - start) * 1000, 0, 0, str(e))

    elapsed = (time.monotonic() - start) * 1000
    data = resp.json()
    usage = data.get("usage") or {}
    # Fall back to a rough estimate only if the provider omitted usage.
    p_tok = usage.get("prompt_tokens")
    c_tok = usage.get("completion_tokens")
    if p_tok is None or c_tok is None:
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        p_tok = p_tok if p_tok is not None else (len(SYSTEM_PROMPT) + len(USER_PROMPT)) // 4
        c_tok = c_tok if c_tok is not None else max(1, len(text) // 4)
    return (True, elapsed, p_tok, c_tok, None)


def _pct(values, p):
    if not values:
        return 0.0
    return statistics.quantiles(values, n=100)[p - 1] if len(values) > 1 else values[0]


async def main() -> int:
    parser = argparse.ArgumentParser(description="HuggingFace backstop cost + latency probe")
    parser.add_argument("n", nargs="?", type=int, default=20, help="number of requests (default 20)")
    parser.add_argument("--model", default=os.getenv("HF_MODEL", DEFAULT_MODEL))
    parser.add_argument("--in-price", type=float, default=DEFAULT_IN_PRICE, help="$ per 1M input tokens")
    parser.add_argument("--out-price", type=float, default=DEFAULT_OUT_PRICE, help="$ per 1M output tokens")
    parser.add_argument("--concurrency", type=int, default=1, help="parallel requests (default 1)")
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    token = os.getenv("HF_TOKEN")
    if not token:
        print("FAIL: HF_TOKEN not set (export it or put it in your environment)", file=sys.stderr)
        return 2

    print(f"Model      : {args.model}")
    print(f"Requests   : {args.n} (concurrency {args.concurrency})")
    print(f"Pricing    : ${args.in_price:.4f}/1M in, ${args.out_price:.4f}/1M out  [EDIT if wrong]")
    print("Running...\n")

    sem = asyncio.Semaphore(args.concurrency)

    async with httpx.AsyncClient() as client:
        async def guarded():
            async with sem:
                return await _one_call(client, args.model, token, args.timeout)

        results = await asyncio.gather(*[guarded() for _ in range(args.n)])

    ok = [r for r in results if r[0]]
    failed = [r for r in results if not r[0]]
    latencies = sorted(r[1] for r in ok)
    in_tokens = sum(r[2] for r in ok)
    out_tokens = sum(r[3] for r in ok)

    in_cost = in_tokens / 1_000_000 * args.in_price
    out_cost = out_tokens / 1_000_000 * args.out_price
    total_cost = in_cost + out_cost
    per_call = total_cost / len(ok) if ok else 0.0

    print("=" * 60)
    print("HUGGINGFACE BACKSTOP COST SMOKE TEST")
    print("=" * 60)
    print(f"OK         : {len(ok)}/{args.n}")
    if failed:
        print(f"Failed     : {len(failed)}  (e.g. {failed[0][4]})")
    if ok:
        print("\nLatency (ms):")
        print(f"  min {latencies[0]:.0f}  p50 {_pct(latencies, 50):.0f}  "
              f"p95 {_pct(latencies, 95):.0f}  max {latencies[-1]:.0f}  "
              f"mean {statistics.mean(latencies):.0f}")
        print("\nTokens:")
        print(f"  input  : {in_tokens:>8,}  (avg {in_tokens / len(ok):.0f}/call)")
        print(f"  output : {out_tokens:>8,}  (avg {out_tokens / len(ok):.0f}/call)")
        print("\nCost:")
        print(f"  input  : ${in_cost:.6f}")
        print(f"  output : ${out_cost:.6f}")
        print(f"  TOTAL  : ${total_cost:.6f}  for {len(ok)} calls")
        print(f"  per call: ${per_call:.6f}")
        print("\nExtrapolated (only the rare all-providers-failed tail hits this):")
        print(f"  1,000 backstop calls : ${per_call * 1_000:.2f}")
        print(f"  10,000 backstop calls: ${per_call * 10_000:.2f}")
        if per_call:
            print(f"  $300 credit lasts    : ~{300 / per_call:,.0f} calls")
    print("=" * 60)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
