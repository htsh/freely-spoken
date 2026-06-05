"""Malformed-output handling: the LLM never produces canonical text, and bad
ids / duplicates / quoted passages are rejected (tasks 7.3, 7.4)."""

import json

import pytest

import app.lookup.dhammapada as d
from app.lookup.base import LookupRequest

from conftest import make_response, stub_llm_returning


REQ = LookupRequest(
    anonymized_text="I had a fight and said cruel things I regret",
    sentiment="negative",
    emotions=["anger", "frustration"],
    confidence=80.0,
)


def _shortlist_ids(req: LookupRequest, n: int = 3) -> list[str]:
    sl = d._shortlist(d._eligible(req.crisis_flag), req)
    return [r["id"] for r in sl[:n]]


async def test_happy_path_enriches_from_catalog(monkeypatch):
    ids = _shortlist_ids(REQ)
    monkeypatch.setattr(d, "run_llm", stub_llm_returning(make_response(ids[0], ids[1:3])))
    res = await d.DhammapadaAdapter().select(REQ)

    # ref is the user-facing displayLabel, text comes from the catalog (not the LLM)
    row = d._CATALOG_BY_ID[ids[0]]
    assert res.primary.ref == row["displayLabel"]
    assert res.primary.text == row["text"]
    assert res.primary.translation == d.TRANSLATION_LABEL
    assert res.primary.textError is None
    assert len(res.alternates) == 2


async def test_nonexistent_id_rejected(monkeypatch):
    ids = _shortlist_ids(REQ)
    payload = make_response("dhp-9999", ids[1:3])
    monkeypatch.setattr(d, "run_llm", stub_llm_returning(payload))
    with pytest.raises(d.DhammapadaAdapterError):
        await d.DhammapadaAdapter().select(REQ)


async def test_duplicate_ids_rejected(monkeypatch):
    ids = _shortlist_ids(REQ)
    payload = make_response(ids[0], [ids[0], ids[1]])  # primary repeated in alternates
    monkeypatch.setattr(d, "run_llm", stub_llm_returning(payload))
    with pytest.raises(d.DhammapadaAdapterError):
        await d.DhammapadaAdapter().select(REQ)


async def test_quoted_passage_text_rejected(monkeypatch):
    ids = _shortlist_ids(REQ)
    payload = make_response(ids[0], ids[1:3])
    # the model dumps the canonical passage into shortReason -> must be rejected,
    # so the LLM can never become a backdoor source of canonical text
    payload["primary"]["shortReason"] = d._CATALOG_BY_ID[ids[0]]["text"]
    monkeypatch.setattr(d, "run_llm", stub_llm_returning(payload))
    with pytest.raises(d.DhammapadaAdapterError):
        await d.DhammapadaAdapter().select(REQ)


async def test_wrong_alternate_count_rejected(monkeypatch):
    ids = _shortlist_ids(REQ, 4)
    payload = {
        "primary": {"id": ids[0], "shortReason": "Fits."},
        "alternates": [{"id": ids[1], "shortReason": "Also fits."}],  # only 1
    }
    monkeypatch.setattr(d, "run_llm", stub_llm_returning(payload))
    with pytest.raises(d.DhammapadaAdapterError):
        await d.DhammapadaAdapter().select(REQ)


async def test_unparseable_output_rejected(monkeypatch):
    async def junk(s, u, *, validate=None):
        from app.llm_runner import LLMResult
        text = "I cannot help with that."
        parsed = validate(text) if validate is not None else None
        return LLMResult(text=text, provider="g", model="m",
                         retry_count=0, fallback_used=False, parsed=parsed)
    monkeypatch.setattr(d, "run_llm", junk)
    with pytest.raises(d.DhammapadaAdapterError):
        await d.DhammapadaAdapter().select(REQ)
