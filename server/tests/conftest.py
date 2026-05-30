"""Shared fixtures and LLM stubs for the Dhammapada adapter tests.

The runtime adapter calls `app.lookup.dhammapada.run_llm`. Tests monkeypatch that
name to avoid any network call, so the suite is hermetic and free to run in CI.
"""

import json
import os
import re

import pytest

from app.llm_runner import LLMResult

_FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
_ID_RE = re.compile(r"dhp-\d+")


@pytest.fixture(scope="session")
def lookup_fixtures() -> list[dict]:
    with open(os.path.join(_FIXTURE_DIR, "lookup_inputs.json"), encoding="utf-8") as fh:
        return json.load(fh)["fixtures"]


def make_response(primary_id: str, alt_ids: list[str]) -> dict:
    """A well-formed selector payload for the given ids."""
    return {
        "primary": {"id": primary_id, "shortReason": "This speaks to your situation."},
        "alternates": [
            {"id": alt_ids[0], "shortReason": "Another angle on it."},
            {"id": alt_ids[1], "shortReason": "A gentle reframing."},
        ],
    }


def stub_llm_returning(payload: dict, *, record: dict | None = None):
    """Async stub that returns `payload` as JSON, optionally recording prompts."""

    async def fake(system_prompt: str, user_prompt: str) -> LLMResult:
        if record is not None:
            record["system"] = system_prompt
            record["user"] = user_prompt
        return LLMResult(
            text=json.dumps(payload),
            provider="gemini",
            model="flash",
            retry_count=0,
            fallback_used=False,
        )

    return fake


def stub_llm_picks_first(*, record: dict | None = None):
    """Async stub that picks the first three ids out of the candidate index it is
    shown. Mirrors a well-behaved model: it can only choose what the adapter put
    in front of it, so it is the right tool for crisis-exclusion property tests."""

    async def fake(system_prompt: str, user_prompt: str) -> LLMResult:
        if record is not None:
            record["system"] = system_prompt
            record["user"] = user_prompt
        ids: list[str] = []
        for m in _ID_RE.findall(user_prompt):
            if m not in ids:
                ids.append(m)
            if len(ids) == 3:
                break
        payload = make_response(ids[0], ids[1:3])
        return LLMResult(
            text=json.dumps(payload),
            provider="gemini",
            model="flash",
            retry_count=0,
            fallback_used=False,
        )

    return fake
