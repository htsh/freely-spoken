"""Per-request fast-tier rotation and per-provider timeouts.

The chain shuffles its "fast tier" to the front of every request so concurrent
load spreads across the fast providers instead of all hammering the same one
first; the rest of the order is a fixed last-resort tail. Each provider is also
invoked with a per-provider timeout so a slow provider can't eat the whole
client budget. These tests pin both at the runner level.
"""

from types import SimpleNamespace

import httpx

import app.llm_runner as r
from app.llm_runner import _effective_order, run
from app.providers import groq


def test_effective_order_keeps_static_order_without_fast_tier():
    order = ["a", "b", "c"]
    assert _effective_order(order, []) == ["a", "b", "c"]


def test_effective_order_puts_fast_tier_first_and_tail_stays_fixed():
    order = ["groq", "cerebras", "mistral", "cloudflare", "openrouter"]
    fast = ["groq", "cerebras", "mistral"]
    # Sample enough times to make a positional bug overwhelmingly likely to show.
    for _ in range(50):
        result = _effective_order(order, fast)
        assert set(result[:3]) == set(fast)          # fast tier occupies the front
        assert result[3:] == ["cloudflare", "openrouter"]  # tail keeps relative order


def test_effective_order_actually_rotates():
    order = ["groq", "cerebras", "mistral", "cloudflare"]
    fast = ["groq", "cerebras", "mistral"]
    firsts = {_effective_order(order, fast)[0] for _ in range(50)}
    # Over many requests, more than one fast provider should lead.
    assert len(firsts) > 1


async def test_per_provider_timeout_passed_to_generate(monkeypatch):
    seen: dict[str, float] = {}

    def _ok_provider(name: str):
        async def generate(system_prompt: str, user_prompt: str, *, timeout: float = 60) -> str:
            seen[name] = timeout
            return "text"
        return generate

    monkeypatch.setattr(
        r, "PROVIDERS",
        {
            "slow": ("m1", _ok_provider("slow")),
            "fast": ("m2", _ok_provider("fast")),
        },
    )
    monkeypatch.setattr(
        r, "SETTINGS",
        SimpleNamespace(
            provider_order=["slow", "fast"],
            fast_tier=[],
            provider_timeouts={"slow": 15},
            default_timeout=60,
            max_retries=3,
        ),
    )

    result = await run("sys", "user")

    assert result.provider == "slow"
    assert seen["slow"] == 15          # override applied
    assert seen.get("fast") is None    # never reached; slow won first


async def test_timeout_falls_through_without_retrying_same_provider(monkeypatch):
    """A timed-out provider must not be retried — that only burns the budget.
    It should fall straight through to the next provider."""
    calls: list[str] = []

    def _timing_out(name: str):
        async def generate(system_prompt: str, user_prompt: str, *, timeout: float = 60) -> str:
            calls.append(name)
            try:
                raise httpx.ReadTimeout("too slow")
            except httpx.ReadTimeout as e:
                raise groq.GroqError("timeout") from e
        return generate

    def _ok(name: str):
        async def generate(system_prompt: str, user_prompt: str, *, timeout: float = 60) -> str:
            calls.append(name)
            return "good"
        return generate

    monkeypatch.setattr(
        r, "PROVIDERS",
        {"slow": ("m1", _timing_out("slow")), "fast": ("m2", _ok("fast"))},
    )
    monkeypatch.setattr(
        r, "SETTINGS",
        SimpleNamespace(
            provider_order=["slow", "fast"],
            fast_tier=[],
            provider_timeouts={},
            default_timeout=60,
            max_retries=3,
        ),
    )

    result = await run("sys", "user")

    assert result.provider == "fast"
    # "slow" was attempted exactly once despite max_retries=3.
    assert calls == ["slow", "fast"]
    assert result.provider_errors["slow"] == "timeout"
