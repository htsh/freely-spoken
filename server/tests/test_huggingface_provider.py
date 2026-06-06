"""Unit tests for the HuggingFace last-resort provider adapter.

HuggingFace is the paid backstop: it is only reached when every free provider
ahead of it has failed, so in normal load it is never exercised. That makes a
direct adapter test important — it is the one place we can prove the parsing and
error handling are correct without waiting for a black-swan request to discover
a broken key, renamed model, or changed response shape.

Hermetic: an httpx.MockTransport stands in for the network. No keys, no calls.
"""

import httpx
import pytest

from app.providers import huggingface


def _patch_transport(monkeypatch, handler):
    """Route the adapter's httpx client through a MockTransport."""
    real_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        return real_client(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(huggingface.httpx, "AsyncClient", factory)


async def test_returns_message_content_on_success(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_test")
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("Authorization")
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "the answer"}}]},
        )

    _patch_transport(monkeypatch, handler)

    text = await huggingface.generate("sys", "user", timeout=5)

    assert text == "the answer"
    assert captured["auth"] == "Bearer hf_test"


async def test_raises_when_token_missing(monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)

    with pytest.raises(huggingface.HuggingFaceError):
        await huggingface.generate("sys", "user", timeout=5)


async def test_raises_on_http_error_with_status_cause(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_test")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": "rate limited"})

    _patch_transport(monkeypatch, handler)

    with pytest.raises(huggingface.HuggingFaceError) as exc:
        await huggingface.generate("sys", "user", timeout=5)
    # The runner inspects __cause__ for the status code to classify 429s.
    assert isinstance(exc.value.__cause__, httpx.HTTPStatusError)
    assert exc.value.__cause__.response.status_code == 429


async def test_raises_on_empty_content(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_test")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "   "}}]})

    _patch_transport(monkeypatch, handler)

    with pytest.raises(huggingface.HuggingFaceError):
        await huggingface.generate("sys", "user", timeout=5)
