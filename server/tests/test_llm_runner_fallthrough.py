"""Malformed output from one provider must fall through to the next.

Before this behavior, a provider that returned HTTP 200 with unusable text (bad
JSON, an out-of-set id) failed the whole request — the chain never advanced even
though a later provider could produce something valid. These tests pin the fix at
the runner level, independent of any adapter.
"""

from types import SimpleNamespace

import pytest

import app.llm_runner as r
from app.llm_runner import (
    AllProvidersFailedError,
    OutputValidationError,
    run,
)


@pytest.fixture
def two_providers(monkeypatch):
    """Replace the provider chain with two named, in-memory generators."""
    calls: list[str] = []

    def _provider(name: str, text: str):
        async def generate(system_prompt: str, user_prompt: str) -> str:
            calls.append(name)
            return text
        return generate

    def configure(first_text: str, second_text: str):
        monkeypatch.setattr(
            r, "PROVIDERS",
            {
                "first": ("m1", _provider("first", first_text)),
                "second": ("m2", _provider("second", second_text)),
            },
        )
        # SETTINGS is a frozen dataclass; swap the whole object the runner reads.
        monkeypatch.setattr(
            r, "SETTINGS",
            SimpleNamespace(provider_order=["first", "second"], max_retries=3),
        )

    return configure, calls


def _validate(text: str):
    if text != "good":
        raise OutputValidationError(f"unusable: {text!r}")
    return {"ok": True}


async def test_malformed_first_provider_falls_through(two_providers):
    configure, calls = two_providers
    configure(first_text="garbage", second_text="good")

    result = await run("sys", "user", validate=_validate)

    assert result.provider == "second"
    assert result.parsed == {"ok": True}
    assert result.fallback_used is True
    # First provider was tried exactly once — no wasteful same-model retry.
    assert calls == ["first", "second"]


async def test_first_provider_wins_when_valid(two_providers):
    configure, calls = two_providers
    configure(first_text="good", second_text="good")

    result = await run("sys", "user", validate=_validate)

    assert result.provider == "first"
    assert result.fallback_used is False
    assert calls == ["first"]


async def test_all_malformed_raises_all_providers_failed(two_providers):
    configure, _ = two_providers
    configure(first_text="bad1", second_text="bad2")

    with pytest.raises(AllProvidersFailedError) as exc:
        await run("sys", "user", validate=_validate)

    # The last validation error is attached for the HTTP layer to log.
    assert isinstance(exc.value.last_error, OutputValidationError)
