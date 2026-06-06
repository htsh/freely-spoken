#!/usr/bin/env python3
"""
Load-test the /lookup endpoint for the Dhammapada variant.

Usage (on a VPS with python3 and httpx installed):

    python3 -m pip install httpx
    python3 server/scripts/load-test-dhammapada.py \
      --host https://verses.hitesh.nyc \
      --secret "$LOOKUP_CLIENT_SECRET" \
      --requests 100 \
      --concurrency 4

Outputs a summary table: success rate, error breakdown, latency percentiles,
provider distribution, and fallback rate.

The script deliberately rotates the request payload so the LLM sees varied
situations (anxiety, anger, grief, gratitude, etc.) rather than a single
cached prompt.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import statistics
import sys
import time
from dataclasses import dataclass, field
from typing import Any

try:
    import httpx
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "httpx is required. Install it with: python3 -m pip install httpx"
    ) from exc


# ── Varied payloads so the LLM doesn't get a trivially cached prompt ──────────

_PAYLOADS: list[dict[str, Any]] = [
    {
        "anonymizedText": "the person feels overwhelmed and wants a quieter way to respond",
        "sentiment": "negative",
        "emotions": ["anxiety", "frustration"],
        "confidence": 65,
    },
    {
        "anonymizedText": "the person is angry about something that was said and regrets speaking",
        "sentiment": "negative",
        "emotions": ["anger", "speech-regret"],
        "confidence": 70,
    },
    {
        "anonymizedText": "the person can't stop wanting something they know is unhealthy",
        "sentiment": "negative",
        "emotions": ["craving"],
        "confidence": 55,
    },
    {
        "anonymizedText": "the person keeps replaying the same worry over and over in their mind",
        "sentiment": "negative",
        "emotions": ["worry", "rumination"],
        "confidence": 60,
    },
    {
        "anonymizedText": "the person feels betrayed by someone close and doesn't know how to move forward",
        "sentiment": "negative",
        "emotions": ["relational-hurt"],
        "confidence": 50,
    },
    {
        "anonymizedText": "the person is ashamed of something they did and can't stop blaming themselves",
        "sentiment": "negative",
        "emotions": ["self-blame"],
        "confidence": 75,
    },
    {
        "anonymizedText": "the person feels grateful for a small kindness they received today",
        "sentiment": "positive",
        "emotions": ["gratitude"],
        "confidence": 80,
    },
    {
        "anonymizedText": "the person is proud of an achievement but worries it makes them arrogant",
        "sentiment": "mixed",
        "emotions": ["pride", "confusion"],
        "confidence": 45,
    },
    {
        "anonymizedText": "the person feels envious of a friend's success and wants to feel happy for them instead",
        "sentiment": "negative",
        "emotions": ["envy"],
        "confidence": 40,
    },
    {
        "anonymizedText": "the person is restless and can't sit still, feeling on edge all day",
        "sentiment": "negative",
        "emotions": ["restlessness"],
        "confidence": 62,
    },
    {
        "anonymizedText": "the person is confused about a big decision and doesn't know which path to take",
        "sentiment": "neutral",
        "emotions": ["confusion", "doubt"],
        "confidence": 50,
    },
    {
        "anonymizedText": "the person just had an argument with a family member and feels terrible about it",
        "sentiment": "negative",
        "emotions": ["conflict", "anger"],
        "confidence": 58,
    },
]


# ── Result tracking ───────────────────────────────────────────────────────────


@dataclass
class Result:
    latency_ms: float
    status: int
    provider: str = ""
    fallback_used: bool = False
    error_code: str = ""  # e.g. "all_providers_failed", "lookup_unavailable"
    raw: str = ""  # body or error text
    request_num: int = 0
    payload_emotion: str = ""  # emotion from the payload for debugging
    providers_attempted: list[str] = field(default_factory=list)  # which providers were tried
    verbose: bool = False  # whether to print per-request details


@dataclass
class Summary:
    total: int = 0
    ok_200: int = 0
    errors: dict[int, int] = field(default_factory=dict)
    provider_counts: dict[str, int] = field(default_factory=dict)
    fallback_count: int = 0
    unavailable_count: int = 0
    latencies: list[float] = field(default_factory=list)
    slowest: Result | None = None
    fastest: Result | None = None
    provider_latencies: dict[str, list[float]] = field(default_factory=dict)  # per-provider latency tracking
    provider_errors: dict[str, int] = field(default_factory=dict)  # per-provider error counts
    all_results: list[Result] = field(default_factory=list)  # full result history for detailed analysis
    chain_depth: dict[int, int] = field(default_factory=dict)  # how many providers were tried (0=timeout, 1=primary, 2=1st fallback, etc.)

    def add(self, r: Result) -> None:
        self.total += 1
        self.latencies.append(r.latency_ms)
        self.all_results.append(r)

        if r.status == 200:
            self.ok_200 += 1
        else:
            self.errors[r.status] = self.errors.get(r.status, 0) + 1

        if r.provider:
            self.provider_counts[r.provider] = self.provider_counts.get(r.provider, 0) + 1
            if r.provider not in self.provider_latencies:
                self.provider_latencies[r.provider] = []
            self.provider_latencies[r.provider].append(r.latency_ms)
            if r.status != 200:
                self.provider_errors[r.provider] = self.provider_errors.get(r.provider, 0) + 1

        # Track chain depth: how many providers were attempted
        depth = len(r.providers_attempted) if r.providers_attempted else 0
        if r.error_code == "timeout":
            depth = 0  # timeout means all providers exhausted
        self.chain_depth[depth] = self.chain_depth.get(depth, 0) + 1

        if r.fallback_used:
            self.fallback_count += 1
        if r.error_code == "lookup_unavailable":
            self.unavailable_count += 1

        if self.slowest is None or r.latency_ms > self.slowest.latency_ms:
            self.slowest = r
        if self.fastest is None or r.latency_ms < self.fastest.latency_ms:
            self.fastest = r


# ── HTTP helpers ──────────────────────────────────────────────────────────────


def _make_payload() -> dict[str, Any]:
    base = random.choice(_PAYLOADS)
    return {
        "appVariant": "dhammapada",
        **base,
    }


async def _request(
    client: httpx.AsyncClient,
    url: str,
    secret: str | None,
    summary: Summary,
    request_num: int = 0,
    verbose: bool = False,
) -> None:
    payload = _make_payload()
    payload_emotion = payload.get("emotions", ["unknown"])[0]  # first emotion for logging

    headers = {"Content-Type": "application/json"}
    if secret:
        headers["X-Lookup-Client-Secret"] = secret

    started = time.perf_counter()
    try:
        resp = await client.post(url, headers=headers, json=payload, timeout=60.0)
    except httpx.TimeoutException as exc:
        latency_ms = (time.perf_counter() - started) * 1000
        result = Result(
            latency_ms=latency_ms,
            status=0,
            raw="httpx timeout",
            error_code="timeout",
            request_num=request_num,
            payload_emotion=payload_emotion,
            verbose=verbose,
        )
        if verbose:
            print(f"  #{request_num}: TIMEOUT {latency_ms:.1f}ms ({payload_emotion})", flush=True)
        summary.add(result)
        return
    except httpx.HTTPStatusError as exc:
        latency_ms = (time.perf_counter() - started) * 1000
        result = Result(
            latency_ms=latency_ms,
            status=exc.response.status_code,
            raw=exc.response.text[:200],
            request_num=request_num,
            payload_emotion=payload_emotion,
            verbose=verbose,
        )
        if verbose:
            print(f"  #{request_num}: HTTP {exc.response.status_code} {latency_ms:.1f}ms ({payload_emotion})", flush=True)
        summary.add(result)
        return
    except Exception as exc:
        latency_ms = (time.perf_counter() - started) * 1000
        result = Result(
            latency_ms=latency_ms,
            status=0,
            raw=str(exc)[:200],
            request_num=request_num,
            payload_emotion=payload_emotion,
            verbose=verbose,
        )
        if verbose:
            print(f"  #{request_num}: ERROR {latency_ms:.1f}ms ({payload_emotion}): {exc}", flush=True)
        summary.add(result)
        return

    latency_ms = (time.perf_counter() - started) * 1000
    body = resp.text

    provider = ""
    fallback_used = False
    error_code = ""
    providers_attempted = []

    if resp.status_code == 200:
        try:
            data = resp.json()
            provider = data.get("provider", "")
            fallback_used = data.get("fallbackUsed", False)
            providers_attempted = data.get("providersAttempted", [])
            if data.get("status") == "lookup_unavailable":
                error_code = "lookup_unavailable"
        except Exception:
            pass
    else:
        try:
            data = resp.json()
            error_code = data.get("error", {}).get("code", "")
        except Exception:
            pass

    result = Result(
        latency_ms=latency_ms,
        status=resp.status_code,
        provider=provider,
        fallback_used=fallback_used,
        error_code=error_code,
        raw=body[:500],
        request_num=request_num,
        payload_emotion=payload_emotion,
        providers_attempted=providers_attempted,
        verbose=verbose,
    )

    if verbose:
        if providers_attempted:
            chain = " → ".join(providers_attempted)
            depth = len(providers_attempted)
        elif provider:
            chain = provider  # backend didn't return full chain, show final provider
            depth = "?"
        else:
            chain = "unknown"
            depth = "?"
        status_str = str(resp.status_code)
        print(f"  #{request_num}: [{depth}] {chain:35} {latency_ms:7.1f}ms {status_str} ({payload_emotion})", flush=True)

    summary.add(result)


async def _worker(
    client: httpx.AsyncClient,
    url: str,
    secret: str | None,
    queue: asyncio.Queue[tuple[int, asyncio.Event]],
    summary: Summary,
    total: int,
    progress_lock: asyncio.Lock,
    progress_counter: list[int],
    verbose: bool = False,
) -> None:
    while True:
        try:
            request_num, done_event = queue.get_nowait()
        except asyncio.QueueEmpty:
            break
        await _request(client, url, secret, summary, request_num=request_num, verbose=verbose)
        async with progress_lock:
            progress_counter[0] += 1
            done = progress_counter[0]
            if not verbose and (done % 5 == 0 or done == total):
                print(f"  ... {done}/{total} completed", flush=True)


async def run(host: str, secret: str | None, requests: int, concurrency: int, verbose: bool = False) -> Summary:
    url = f"{host.rstrip('/')}/lookup"
    summary = Summary()
    queue: asyncio.Queue[tuple[int, asyncio.Event]] = asyncio.Queue()
    for i in range(requests):
        queue.put_nowait((i + 1, asyncio.Event()))

    progress_lock = asyncio.Lock()
    progress_counter: list[int] = [0]

    limits = httpx.Limits(max_connections=concurrency * 2, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(limits=limits, http2=False) as client:
        workers = [
            asyncio.create_task(
                _worker(client, url, secret, queue, summary, requests, progress_lock, progress_counter, verbose=verbose)
            )
            for _ in range(concurrency)
        ]
        await asyncio.gather(*workers)

    return summary


# ── Reporting ───────────────────────────────────────────────────────────────────


def _p(latencies: list[float], pct: float) -> float:
    if not latencies:
        return 0.0
    sorted_l = sorted(latencies)
    idx = int((pct / 100.0) * (len(sorted_l) - 1))
    return sorted_l[idx]


def report(summary: Summary) -> None:
    print("\n" + "=" * 70)
    print("LOAD TEST SUMMARY")
    print("=" * 70)

    print(f"\nTotal requests : {summary.total}")
    print(f"OK (HTTP 200)  : {summary.ok_200} ({100 * summary.ok_200 / summary.total:.1f}%)")

    if summary.errors:
        print("\nErrors by status:")
        for code, count in sorted(summary.errors.items()):
            print(f"  {code:>3} : {count} ({100 * count / summary.total:.1f}%)")
    else:
        print("\nErrors by status: none")

    if summary.latencies:
        lats = summary.latencies
        print(f"\nOverall latency (ms):")
        print(f"  min : {min(lats):.1f}")
        print(f"  p50 : {_p(lats, 50):.1f}")
        print(f"  p95 : {_p(lats, 95):.1f}")
        print(f"  p99 : {_p(lats, 99):.1f}")
        print(f"  max : {max(lats):.1f}")
        print(f"  mean: {statistics.mean(lats):.1f}")

    if summary.provider_counts:
        print(f"\nProvider breakdown:")
        for prov, count in sorted(summary.provider_counts.items(), key=lambda x: -x[1]):
            prov_lats = summary.provider_latencies.get(prov, [])
            prov_errors = summary.provider_errors.get(prov, 0)
            prov_success_rate = (count - prov_errors) / count * 100 if count > 0 else 0
            if prov_lats:
                prov_p95 = _p(prov_lats, 95)
                prov_mean = statistics.mean(prov_lats)
                print(f"  {prov:12} : {count:2}  {prov_success_rate:5.1f}% OK  p95={prov_p95:7.1f}ms  mean={prov_mean:7.1f}ms")
            else:
                print(f"  {prov:12} : {count:2}  (no successful latency data)")
        if summary.fallback_count:
            print(f"\n  Fallback triggered: {summary.fallback_count} ({100 * summary.fallback_count / summary.total:.1f}%)")
    else:
        print("\nProviders used: none parsed (all errors?)")

    if summary.unavailable_count:
        print(f"\nLookup unavailable (crisis filter): {summary.unavailable_count}")

    # Chain depth distribution — shows how stressed the backend is
    if summary.chain_depth:
        has_chain_data = any(d > 0 for d in summary.chain_depth)
        print(f"\nProvider chain depth (how many providers tried):")
        if not has_chain_data:
            print("  (backend not returning providersAttempted — upgrade backend for full chain visibility)")
        provider_names = ["groq", "cerebras", "cloudflare", "openrouter", "cohere", "together"]
        for depth in sorted(summary.chain_depth.keys()):
            count = summary.chain_depth[depth]
            pct = 100 * count / summary.total
            if depth == 0:
                print(f"  [TIMEOUT]           : {count:2} ({pct:5.1f}%) — all providers exhausted")
            else:
                chain = " → ".join(provider_names[:depth])
                print(f"  [{depth}] {chain:35} : {count:2} ({pct:5.1f}%)")

    # Slowest requests breakdown
    if len(summary.all_results) > 0:
        print(f"\nSlowest 3 requests:")
        sorted_by_latency = sorted(summary.all_results, key=lambda r: -r.latency_ms)[:3]
        for r in sorted_by_latency:
            fb_note = " [FALLBACK]" if r.fallback_used else ""
            print(f"  #{r.request_num}: {r.provider or 'NONE':12} {r.latency_ms:7.1f}ms status={r.status} ({r.payload_emotion}){fb_note}")
            if r.error_code:
                print(f"           Error: {r.error_code}")
            if r.providers_attempted:
                print(f"           Attempted: {', '.join(r.providers_attempted)}")

    if summary.fastest and summary.slowest:
        print(f"\nFastest request: {summary.fastest.latency_ms:.1f} ms  (status {summary.fastest.status})")
        print(f"Slowest request: {summary.slowest.latency_ms:.1f} ms  (status {summary.slowest.status})")
        if summary.slowest.status != 200 and summary.slowest.raw:
            print(f"  Slowest body: {summary.slowest.raw[:200]}")

    print("=" * 70)


# ── CLI ─────────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="https://verses.hitesh.nyc", help="Base URL of the backend (default: https://verses.hitesh.nyc)")
    parser.add_argument("--secret", default="", help="X-Lookup-Client-Secret header value (falls back to $LOOKUP_CLIENT_SECRET)")
    parser.add_argument("--requests", type=int, default=50, help="Total number of requests to send (default: 50)")
    parser.add_argument("--concurrency", type=int, default=4, help="Number of concurrent workers (default: 4)")
    parser.add_argument("--delay", type=float, default=0.0, help="Delay in seconds between each request (default: 0)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Log each request with provider, latency, and status")
    args = parser.parse_args(argv)
    secret = args.secret or os.environ.get("LOOKUP_CLIENT_SECRET", "")

    if args.requests < 1:
        parser.error("--requests must be >= 1")
    if args.concurrency < 1:
        parser.error("--concurrency must be >= 1")

    print(f"Target: {args.host}/lookup")
    print(f"Requests: {args.requests}  Concurrency: {args.concurrency}  Delay: {args.delay}s")
    if args.verbose:
        print("Verbose mode: ON")
    print("Starting load test...")

    # If delay is requested, we throttle by using a single worker with sleep
    if args.delay > 0:
        # Simple sequential mode with sleep
        async def sequential():
            summary = Summary()
            limits = httpx.Limits(max_connections=1, max_keepalive_connections=1)
            async with httpx.AsyncClient(limits=limits) as client:
                for i in range(args.requests):
                    await _request(
                        client,
                        f"{args.host.rstrip('/')}/lookup",
                        secret or None,
                        summary,
                        request_num=i + 1,
                        verbose=args.verbose,
                    )
                    if not args.verbose:
                        print(f"  ... {i + 1}/{args.requests} completed", flush=True)
                    if i < args.requests - 1:
                        await asyncio.sleep(args.delay)
            return summary
        summary = asyncio.run(sequential())
    else:
        summary = asyncio.run(run(args.host, secret or None, args.requests, args.concurrency, verbose=args.verbose))

    report(summary)
    return 0 if summary.ok_200 == summary.total else 1


if __name__ == "__main__":
    sys.exit(main())
