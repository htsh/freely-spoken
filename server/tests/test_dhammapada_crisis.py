"""Crisis-flag behavior — the load-bearing safety contract.

- The LLM prompt does NOT branch on crisis state; only the candidate index shrinks (7.6).
- Hard-excluded passages never appear in primary/alternates under crisisFlag,
  regardless of LLM output (7.7).
- Too few eligible passages -> lookup_unavailable, never a degraded answer (7.8).
"""

import pytest

import app.lookup.dhammapada as d
from app.lookup.base import LookupRequest

from conftest import make_response, stub_llm_returning, stub_llm_picks_first


def _req(text="I feel hopeless and ashamed, I keep blaming myself", *, crisis):
    return LookupRequest(
        anonymized_text=text, sentiment="negative",
        emotions=["sadness", "fear"], confidence=85.0, crisis_flag=crisis,
    )


_CRISIS_WORDS = ["crisis", "suicid", "self-harm", "self harm", "distress",
                 "emergency", "in danger", "harm yourself"]


async def test_prompt_does_not_branch_on_crisis(monkeypatch):
    """Same input, crisis off vs on: the system prompt is identical and contains
    no crisis language; the only difference is a smaller candidate index (7.6)."""
    rec_off, rec_on = {}, {}

    monkeypatch.setattr(d, "run_llm", stub_llm_picks_first(record=rec_off))
    await d.DhammapadaAdapter().select(_req(crisis=False))

    monkeypatch.setattr(d, "run_llm", stub_llm_picks_first(record=rec_on))
    await d.DhammapadaAdapter().select(_req(crisis=True))

    assert rec_off["system"] == rec_on["system"]
    blob = (rec_on["system"] + "\n" + rec_on["user"]).lower()
    for w in _CRISIS_WORDS:
        assert w not in blob, f"crisis word {w!r} leaked into the prompt"


async def test_crisis_index_excludes_high_risk_passages(monkeypatch):
    """Across all fixtures, with crisisFlag the LLM is only ever shown — and so
    can only return — eligible passages (7.7)."""
    rec = {}
    monkeypatch.setattr(d, "run_llm", stub_llm_picks_first(record=rec))
    res = await d.DhammapadaAdapter().select(_req(crisis=True))
    for ref in [res.primary, *res.alternates]:
        # map displayLabel back to the row and assert it is not hard-excluded
        row = next(r for r in d._CATALOG if r["displayLabel"] == ref.ref)
        assert not d._excluded(row), f"{row['id']} is crisis-excluded but was returned"
    # and no crisis id appeared in the candidate index the model saw
    import re
    shown = set(re.findall(r"dhp-\d+", rec["user"]))
    for rid in shown:
        assert not d._excluded(d._CATALOG_BY_ID[rid]), f"{rid} leaked into crisis index"


async def test_llm_cannot_force_an_excluded_passage(monkeypatch):
    """Even if the model returns an excluded id, the adapter rejects it as
    malformed rather than surfacing it (7.7)."""
    excluded = next(r for r in d._CATALOG if d._excluded(r))
    eligible_alts = [r["id"] for r in d._CATALOG if not d._excluded(r)][:2]
    payload = make_response(excluded["id"], eligible_alts)
    monkeypatch.setattr(d, "run_llm", stub_llm_returning(payload))
    with pytest.raises(d.DhammapadaAdapterError):
        await d.DhammapadaAdapter().select(_req(crisis=True))


async def test_too_few_eligible_returns_lookup_unavailable(monkeypatch):
    """When crisis exclusion leaves < 3 eligible, raise LookupUnavailableError
    before any LLM call — never relax the filter (7.8)."""
    # shrink the catalog to 2 rows so the eligible set is < 3 under crisis
    monkeypatch.setattr(d, "_CATALOG", d._CATALOG[:2])

    called = {"n": 0}
    async def must_not_call(s, u):
        called["n"] += 1
        raise AssertionError("LLM must not be called when lookup is unavailable")
    monkeypatch.setattr(d, "run_llm", must_not_call)

    with pytest.raises(d.LookupUnavailableError):
        await d.DhammapadaAdapter().select(_req(crisis=True))
    assert called["n"] == 0


async def test_non_crisis_uses_full_catalog(monkeypatch):
    """Sanity: without crisisFlag the eligible set is the whole catalog."""
    assert len(d._eligible(False)) == len(d._CATALOG)
    assert len(d._eligible(True)) < len(d._CATALOG)
