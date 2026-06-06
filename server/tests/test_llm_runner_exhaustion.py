"""When the whole chain fails, the raised error must carry enough operational
context to alert on (which providers were tried, why each failed) — without ever
carrying user body text. The HTTP layer hands this straight to Sentry.
"""

from types import SimpleNamespace

import httpx
import pytest

import app.llm_runner as r
from app.llm_runner import AllProvidersFailedError, run
from app.providers import groq


def _failing(name: str, status: int):
    async def generate(system_prompt: str, user_prompt: str, *, timeout: float = 60) -> str:
        request = httpx.Request("POST", "https://example.test")
        response = httpx.Response(status, request=request)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise groq.GroqError(f"{name} failed") from e

    return generate


async def test_exhaustion_carries_attempted_providers_and_reasons(monkeypatch):
    monkeypatch.setattr(
        r, "PROVIDERS",
        {
            "alpha": ("m1", _failing("alpha", 429)),
            "beta": ("m2", _failing("beta", 500)),
        },
    )
    monkeypatch.setattr(
        r, "SETTINGS",
        SimpleNamespace(
            provider_order=["alpha", "beta"],
            fast_tier=[],
            provider_timeouts={},
            default_timeout=60,
            max_retries=1,
        ),
    )

    with pytest.raises(AllProvidersFailedError) as exc:
        await run("sys", "user")

    assert exc.value.providers_attempted == ["alpha", "beta"]
    assert exc.value.provider_errors == {"alpha": "rate_limited", "beta": "http_500"}
    # The body text must never ride along on the error.
    assert "user" not in repr(exc.value)
    assert "sys" not in repr(exc.value)
