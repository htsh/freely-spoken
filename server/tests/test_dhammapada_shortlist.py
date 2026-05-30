"""Shortlist behavior: fixture inputs surface on-axis candidates (7.1/7.2 floor)
and entries tagged with a matching avoidWhen are deprioritized (7.5)."""

import app.lookup.dhammapada as d
from app.lookup.base import LookupRequest


def _req(fx: dict) -> LookupRequest:
    return LookupRequest(
        anonymized_text=fx["anonymizedText"],
        sentiment=fx["sentiment"],
        emotions=fx["emotions"],
        confidence=fx["confidence"],
    )


def test_fixtures_shortlist_overlaps_expected_axis(lookup_fixtures):
    """Automated floor for 7.2: for each fixture with an expected axis, at least
    one of the top-5 shortlist candidates overlaps the expected useWhen/themes.
    (Final tone review of LLM-selected passages remains a human task.)"""
    misses = []
    for fx in lookup_fixtures:
        expect_uw = set(fx.get("expectUseWhen", []))
        expect_th = set(fx.get("expectThemes", []))
        if not expect_uw and not expect_th:
            continue  # shame: intentionally no positive axis (safety-dominated)
        top = d._shortlist(d._eligible(False), _req(fx))[:5]
        hit = any(
            (expect_uw & set(r["useWhen"])) or (expect_th & set(r["themes"]))
            for r in top
        )
        if not hit:
            misses.append(fx["name"])
    assert not misses, f"shortlist found no on-axis candidate for: {misses}"


def test_fixtures_always_yield_enough_candidates(lookup_fixtures):
    for fx in lookup_fixtures:
        sl = d._shortlist(d._eligible(False), _req(fx))
        assert len(sl) >= 3, f"{fx['name']} produced < 3 candidates"


def test_avoidwhen_penalizes_matching_vulnerable_state():
    """Deterministic unit test of the soft penalty (7.5): two otherwise-identical
    candidates rank with the avoidWhen-tagged one lower when the user shows that
    vulnerable state."""
    base = {
        "emotionalFit": ["sadness"], "useWhen": ["discouragement"],
        "themes": ["impermanence"], "tone": "gentle",
    }
    clean = {**base, "id": "dhp-clean", "avoidWhen": []}
    tagged = {**base, "id": "dhp-tagged", "avoidWhen": ["acute-shame", "self-blame"]}

    req = LookupRequest(
        anonymized_text="I feel so ashamed and I blame myself for everything",
        sentiment="negative", emotions=["sadness"], confidence=70.0,
    )
    ranked = d._shortlist([tagged, clean], req)
    assert ranked[0]["id"] == "dhp-clean"
    assert ranked[1]["id"] == "dhp-tagged"


def test_harsh_tone_mildly_deprioritized_all_else_equal():
    base = {
        "emotionalFit": ["anger"], "useWhen": ["anger"], "themes": ["anger"],
        "avoidWhen": [],
    }
    gentle = {**base, "id": "dhp-gentle", "tone": "gentle"}
    stern = {**base, "id": "dhp-stern", "tone": "stern"}
    req = LookupRequest(
        anonymized_text="I am so angry right now",
        sentiment="negative", emotions=["anger"], confidence=70.0,
    )
    ranked = d._shortlist([stern, gentle], req)
    assert ranked[0]["id"] == "dhp-gentle"
