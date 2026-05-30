"""Catalog integrity + crisis-predicate parity with the frozen vocabulary."""

import json
import os

import app.lookup.dhammapada as d

_VOCAB_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "tools", "dhammapada-labeling", "vocabulary.json",
)

_REQUIRED = [
    "id", "displayLabel", "text", "themes", "useWhen", "avoidWhen",
    "tone", "summary", "emotionalFit", "excludeOnCrisis",
]


def test_catalog_loads_with_unique_ids_and_required_fields():
    rows = d._CATALOG
    assert len(rows) == 414
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)), "duplicate ids in catalog"
    for r in rows:
        for key in _REQUIRED:
            assert key in r, f"{r.get('id')} missing {key}"
        assert r["text"].strip(), f"{r['id']} has empty text"


def test_catalog_labels_within_frozen_vocabulary():
    vocab = json.load(open(_VOCAB_PATH, encoding="utf-8"))
    tones = set(vocab["tone"])
    themes = set(vocab["themes"])
    use_when = set(vocab["useWhen"])
    avoid_when = set(vocab["avoidWhen"])
    fit = set(vocab["emotionalFit"])
    for r in d._CATALOG:
        assert r["tone"] in tones, f"{r['id']} bad tone {r['tone']}"
        assert set(r["themes"]) <= themes, f"{r['id']} OOV themes"
        assert set(r["useWhen"]) <= use_when, f"{r['id']} OOV useWhen"
        assert set(r["avoidWhen"]) <= avoid_when, f"{r['id']} OOV avoidWhen"
        assert set(r["emotionalFit"]) <= fit, f"{r['id']} OOV emotionalFit"


def test_crisis_predicate_matches_frozen_vocabulary():
    """The adapter's embedded crisis sets must equal vocabulary.json so a vocab
    bump cannot silently desync the runtime filter from the labels."""
    che = json.load(open(_VOCAB_PATH, encoding="utf-8"))["crisisHardExclusion"]
    assert set(che["tones"]) == set(d.CRISIS_TONES)
    assert set(che["themes"]) == set(d.CRISIS_THEMES)
    assert set(che["avoidWhenCrisisAdjacent"]) == set(d.CRISIS_AVOID_WHEN)


def test_crisis_eligible_count_is_stable():
    """Guards the 260-eligible figure the human review signed off on.
    A change here means the catalog or predicate shifted and needs re-review."""
    eligible = [r for r in d._CATALOG if not d._excluded(r)]
    assert len(eligible) == 260
