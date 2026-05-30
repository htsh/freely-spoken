#!/usr/bin/env python3
"""Validate a Dhammapada catalog file against the frozen schema + vocabulary.

Development-only check. Pure stdlib — no pip deps. The single source of truth
for allowed values is vocabulary.json; this script loads it rather than
hardcoding enums, so a vocabulary version bump cannot silently drift from the
validator.

It validates two row states:
  - seed row    canonical + provenance-constant fields set; retrieval metadata
                empty (post seed_catalog.py, pre-labeling).
  - labeled row retrieval metadata populated; cardinality/vocabulary/cross-field
                rules enforced.

Usage:
    python validate.py catalog.seed.json
    python validate.py outputs/catalog.labeled.json --require-labeled
    python validate.py --dump-schema     # print the derived JSON Schema sketch

Exit code 0 if valid, 1 if any errors.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
# Override with --vocab when validating a revised vocabulary during a future
# catalog pass.
DEFAULT_VOCAB = os.path.join(HERE, "vocabulary.json")

ID_RE = re.compile(r"^dhp-\d{3}$")
GROUPED_VERSES = {58, 87, 104, 153, 195, 229, 256, 268, 271}

CARDINALITY = {  # field -> (min, max)
    "themes": (1, 4),
    "useWhen": (1, 5),
    "emotionalFit": (1, 5),
}

CANONICAL_REQUIRED = [
    "id", "tradition", "source", "chapter", "chapterNumber", "verseNumber",
    "passageRef", "displayLabel", "text", "translator", "sourceUrl",
    "publicDomainStatus", "licenseNote",
]


def load_vocab(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def is_labeled(row):
    """A row is 'labeled' once any retrieval-metadata field is populated."""
    return bool(row.get("themes") or row.get("tone") or row.get("summary")
                or row.get("labeledBy"))


def check_iso8601(value):
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except (ValueError, AttributeError):
        return False


def validate_row(row, vocab, errors, require_labeled):
    rid = row.get("id", "<no-id>")

    def err(msg):
        errors.append(f"{rid}: {msg}")

    # --- canonical / structural ---
    for f in CANONICAL_REQUIRED:
        if not row.get(f) and row.get(f) != 0:
            err(f"missing/empty canonical field '{f}'")

    if not ID_RE.match(str(row.get("id", ""))):
        err(f"id does not match dhp-NNN")
    vn = row.get("verseNumber")
    if isinstance(vn, int):
        if not (1 <= vn <= 423):
            err(f"verseNumber {vn} out of 1..423")
        if row.get("id") != f"dhp-{vn:03d}":
            err(f"id should be dhp-{vn:03d}")
    cn = row.get("chapterNumber")
    if not (isinstance(cn, int) and 1 <= cn <= 26):
        err(f"chapterNumber {cn} out of 1..26")

    vne = row.get("verseNumberEnd")
    if vne is not None:
        if vn not in GROUPED_VERSES:
            err(f"verseNumberEnd present but {vn} is not a known grouped couplet")
        if vne != (vn or 0) + 1:
            err(f"verseNumberEnd {vne} should be verseNumber+1")

    labeled = is_labeled(row)
    if require_labeled and not labeled:
        err("row is unlabeled but --require-labeled was set")
    if not labeled:
        return  # seed row: skip retrieval-metadata checks

    # --- retrieval metadata (labeled rows only) ---
    for field, allowed_key in (("themes", "themes"), ("useWhen", "useWhen"),
                               ("avoidWhen", "avoidWhen"),
                               ("emotionalFit", "emotionalFit"),
                               ("vulnerableStatesToAvoid", "vulnerableStatesToAvoid")):
        vals = row.get(field) or []
        allowed = set(vocab[allowed_key])
        bad = [v for v in vals if v not in allowed]
        if bad:
            err(f"{field} has out-of-vocabulary values: {bad}")

    tone = row.get("tone")
    if tone not in set(vocab["tone"]):
        err(f"tone '{tone}' not in vocabulary")

    for field, (lo, hi) in CARDINALITY.items():
        n = len(row.get(field) or [])
        if not (lo <= n <= hi):
            err(f"{field} has {n} values, expected {lo}..{hi}")

    use = set(row.get("useWhen") or [])
    avoid = set(row.get("avoidWhen") or [])
    overlap = use & avoid
    if overlap:
        err(f"states in both useWhen and avoidWhen: {sorted(overlap)}")

    vsa = set(row.get("vulnerableStatesToAvoid") or [])
    if not vsa <= avoid:
        err(f"vulnerableStatesToAvoid not a subset of avoidWhen: {sorted(vsa - avoid)}")

    if not (row.get("summary") or "").strip():
        err("summary empty on labeled row")
    for f in ("labeledBy", "promptVersion"):
        if not (row.get(f) or "").strip():
            err(f"provenance field '{f}' empty on labeled row")
    if not check_iso8601(row.get("labeledAt") or ""):
        err(f"labeledAt not ISO 8601: {row.get('labeledAt')!r}")
    if not isinstance(row.get("excludeOnCrisis"), bool):
        err("excludeOnCrisis must be boolean")
    rb = row.get("reviewedBy")
    if rb is not None and not isinstance(rb, str):
        err("reviewedBy must be string or null")


def validate_catalog(catalog, vocab, require_labeled, subset=False):
    rows = catalog["rows"] if isinstance(catalog, dict) and "rows" in catalog else catalog
    errors = []

    ids, verses = {}, {}
    covered = set()
    for row in rows:
        validate_row(row, vocab, errors, require_labeled)
        rid = row.get("id")
        if rid in ids:
            errors.append(f"{rid}: duplicate id")
        ids[rid] = True
        vn = row.get("verseNumber")
        if vn in verses:
            errors.append(f"duplicate verseNumber {vn}")
        verses[vn] = True
        if isinstance(vn, int):
            covered.add(vn)
            if row.get("verseNumberEnd"):
                covered.add(row["verseNumberEnd"])

    if not subset:
        missing = sorted(set(range(1, 424)) - covered)
        if missing:
            errors.append(f"verse numbers not covered by any row: {missing}")
    return errors, len(rows), len(covered)


def dump_schema(vocab):
    """A human-facing JSON Schema sketch derived from the frozen vocab."""
    enum = lambda k: {"type": "array", "items": {"enum": vocab[k]}}
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Dhammapada catalog row (labeled)",
        "type": "object",
        "required": CANONICAL_REQUIRED + ["themes", "useWhen", "tone", "summary",
                                          "emotionalFit", "excludeOnCrisis",
                                          "labeledBy", "labeledAt", "promptVersion"],
        "properties": {
            "id": {"type": "string", "pattern": "^dhp-\\d{3}$"},
            "verseNumber": {"type": "integer", "minimum": 1, "maximum": 423},
            "verseNumberEnd": {"type": "integer", "minimum": 2, "maximum": 423},
            "themes": {**enum("themes"), "minItems": 1, "maxItems": 4},
            "useWhen": {**enum("useWhen"), "minItems": 1, "maxItems": 5},
            "avoidWhen": enum("avoidWhen"),
            "emotionalFit": {**enum("emotionalFit"), "minItems": 1, "maxItems": 5},
            "vulnerableStatesToAvoid": enum("vulnerableStatesToAvoid"),
            "tone": {"enum": vocab["tone"]},
            "summary": {"type": "string", "minLength": 1},
            "riskNotes": {"type": ["string", "null"]},
            "excludeOnCrisis": {"type": "boolean"},
            "labeledBy": {"type": "string"},
            "labeledAt": {"type": "string", "format": "date-time"},
            "promptVersion": {"type": "string"},
            "reviewedBy": {"type": ["string", "null"]},
        },
    }
    print(json.dumps(schema, indent=2))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("catalog", nargs="?", help="catalog JSON to validate")
    ap.add_argument("--vocab", default=DEFAULT_VOCAB)
    ap.add_argument("--require-labeled", action="store_true",
                    help="fail rows that are still seed-only (unlabeled)")
    ap.add_argument("--subset", action="store_true",
                    help="skip the full 1..423 verse-coverage check (for eval subsets)")
    ap.add_argument("--dump-schema", action="store_true",
                    help="print derived JSON Schema sketch and exit")
    args = ap.parse_args(argv)

    vocab = load_vocab(args.vocab)
    if args.dump_schema:
        dump_schema(vocab)
        return 0
    if not args.catalog:
        ap.error("catalog path required (or use --dump-schema)")

    with open(args.catalog, encoding="utf-8") as fh:
        catalog = json.load(fh)

    errors, n_rows, n_covered = validate_catalog(
        catalog, vocab, args.require_labeled, subset=args.subset)
    if errors:
        print(f"INVALID: {len(errors)} error(s) across {n_rows} rows")
        for e in errors[:100]:
            print(f"  - {e}")
        if len(errors) > 100:
            print(f"  ... and {len(errors) - 100} more")
        return 1
    print(f"OK: {n_rows} rows valid, {n_covered}/423 verse numbers covered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
