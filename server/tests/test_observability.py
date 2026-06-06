"""Sentry reporting for the 'all providers failed' black-swan event.

Two properties matter:
1. It reports operational context (which providers were tried, why) so the alert
   is actionable.
2. It NEVER sends user body text. The reporter is only handed provider metadata,
   and Sentry is initialized with body scrubbing as defense in depth.

Hermetic: a fake stands in for sentry_sdk. No DSN, no network.
"""

from types import SimpleNamespace

import app.observability as obs
from app.llm_runner import AllProvidersFailedError


class _FakeScope:
    def __init__(self):
        self.tags: dict = {}
        self.contexts: dict = {}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def set_tag(self, key, value):
        self.tags[key] = value

    def set_context(self, key, value):
        self.contexts[key] = value


class _FakeSentry:
    def __init__(self):
        self.scope = _FakeScope()
        self.messages: list = []

    def new_scope(self):
        return self.scope

    def capture_message(self, message, level=None):
        self.messages.append((message, level))


def test_report_is_noop_when_uninitialized(monkeypatch):
    # No DSN configured: must not raise, must not touch sentry.
    fake = _FakeSentry()
    monkeypatch.setattr(obs, "sentry_sdk", fake)
    monkeypatch.setattr(obs, "_initialized", False)

    err = AllProvidersFailedError(ValueError("x"), providers_attempted=["groq"])
    obs.report_all_providers_failed(request_id="r1", variant="dhammapada", error=err)

    assert fake.messages == []


def test_report_sends_provider_context_without_body(monkeypatch):
    fake = _FakeSentry()
    monkeypatch.setattr(obs, "sentry_sdk", fake)
    monkeypatch.setattr(obs, "_initialized", True)

    err = AllProvidersFailedError(
        RuntimeError("groq 429"),
        providers_attempted=["groq", "mistral", "huggingface"],
        provider_errors={"groq": "rate_limited", "mistral": "timeout", "huggingface": "http_500"},
    )
    obs.report_all_providers_failed(request_id="req-123", variant="christian", error=err)

    assert fake.messages == [("all_providers_failed", "error")]
    assert fake.scope.tags["variant"] == "christian"
    assert fake.scope.tags["lookup_request_id"] == "req-123"
    chain = fake.scope.contexts["provider_chain"]
    assert chain["attempted"] == ["groq", "mistral", "huggingface"]
    assert chain["errors"]["mistral"] == "timeout"


def test_scrub_body_strips_request_data():
    event = {"request": {"data": {"anonymizedText": "secret"}, "url": "/lookup", "cookies": "x"}}
    cleaned = obs._scrub_body(event, {})
    assert "data" not in cleaned["request"]
    assert "cookies" not in cleaned["request"]
    assert cleaned["request"]["url"] == "/lookup"
