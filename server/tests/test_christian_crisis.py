"""Christian crisis-guardrail behavior.

The Christian adapter lets the model pick from all of scripture, so — unlike the
Dhammapada adapter, which shrinks a candidate set the model never sees — the only
lever for crisis safety is the prompt. These tests pin that:

- without a crisis flag the system prompt is the base prompt, byte-for-byte;
- with a crisis flag a guardrail is appended that steers toward comfort and
  explicitly away from judgment / wrath / condemnation;
- the guardrail keeps its load-bearing wording;
- adding it does not break normal selection or parsing.

Hermetic: the LLM call and the Bible-API enrichment are both stubbed, so no key
or network is required.
"""

import pytest

import app.lookup.christian as c
from app.lookup.base import LookupRequest

from conftest import stub_llm_returning


def _payload() -> dict:
    """A well-formed Christian selector payload (refs + short reasons only)."""
    return {
        "primary": {
            "ref": "Psalm 34:18",
            "shortReason": "It speaks to being close to the brokenhearted.",
        },
        "alternates": [
            {"ref": "Matthew 11:28", "shortReason": "An invitation to rest."},
            {"ref": "Isaiah 41:10", "shortReason": "A reassurance not to fear."},
        ],
    }


def _req(*, crisis: bool) -> LookupRequest:
    return LookupRequest(
        anonymized_text="the person feels overwhelmed and alone",
        sentiment="negative",
        emotions=["sadness", "fear"],
        confidence=0.7,
        crisis_flag=crisis,
    )


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Never hit bible-api here; text enrichment is exercised by other tests."""

    async def _noop(refs):
        return None

    monkeypatch.setattr(c, "_enrich_with_text", _noop)


async def test_non_crisis_uses_base_prompt_unchanged(monkeypatch):
    """No crisis flag -> the model sees exactly the base prompt, unperturbed."""
    rec: dict = {}
    monkeypatch.setattr(c, "run_llm", stub_llm_returning(_payload(), record=rec))

    await c.ChristianAdapter().select(_req(crisis=False))

    assert rec["system"] == c.CHRISTIAN_SYSTEM_PROMPT


async def test_crisis_appends_guardrail(monkeypatch):
    """Crisis flag -> the base prompt plus the guardrail, in that order."""
    rec: dict = {}
    monkeypatch.setattr(c, "run_llm", stub_llm_returning(_payload(), record=rec))

    await c.ChristianAdapter().select(_req(crisis=True))

    system = rec["system"]
    assert system.startswith(c.CHRISTIAN_SYSTEM_PROMPT)
    assert c.CHRISTIAN_CRISIS_GUARDRAIL in system
    assert system != c.CHRISTIAN_SYSTEM_PROMPT


def test_guardrail_keeps_critical_avoidances_and_comforts():
    """Pin the load-bearing wording so a future edit can't quietly gut it."""
    text = c.CHRISTIAN_CRISIS_GUARDRAIL.lower()
    for avoid in ("judgment", "wrath", "punishment", "condemnation", "rebuke"):
        assert avoid in text, f"guardrail no longer warns against {avoid!r}"
    for comfort in ("comfort", "refuge"):
        assert comfort in text, f"guardrail no longer steers toward {comfort!r}"


async def test_crisis_still_returns_wellformed_result(monkeypatch):
    """The guardrail must not break normal selection/validation."""
    monkeypatch.setattr(c, "run_llm", stub_llm_returning(_payload()))

    result = await c.ChristianAdapter().select(_req(crisis=True))

    assert result.primary.ref == "Psalm 34:18"
    assert len(result.alternates) == 2
