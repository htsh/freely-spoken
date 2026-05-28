#!/usr/bin/env python3
"""Seed the Dhammapada catalog skeleton from Project Gutenberg #2017 (Müller).

Development-only data-prep tool (task 2.3). Parses the canonical F. Max Müller
translation into structured catalog rows, populating the canonical-content and
provenance fields. Retrieval-metadata fields (themes, useWhen, tone, ...) are
left empty for the LLM labeling pass (tasks 2.5-2.6) to fill.

This script NEVER writes retrieval metadata and NEVER invents canonical text:
it only transcribes and structures what is in the public-domain source.

Usage:
    python seed_catalog.py --source URL_OR_PATH --out outputs/catalog.seed.json
    python seed_catalog.py --grouping verse   # 423 rows, split couplets
    python seed_catalog.py --grouping passage  # default: 1 row per paragraph

Grouping modes (see the "Grouped couplets" note in catalog-schema.md):
    passage  Müller groups 9 verse pairs (e.g. "58, 59.") into one paragraph
             of continuous text. In passage mode each paragraph is one row;
             grouped pairs get a verse range (verseNumber=58, verseNumberEnd=59,
             passageRef="Dhammapada 58-59"). Yields 414 rows covering 1-423.
    verse    Each of the 423 verse numbers becomes its own row; grouped pairs
             duplicate the shared paragraph text. Yields 423 rows.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone

DEFAULT_SOURCE = "https://www.gutenberg.org/files/2017/2017-h/2017-h.htm"

# Provenance constants — single source of truth is rights-review.md § 1.3.
TRANSLATOR = "F. Max Müller"
SOURCE_URL = DEFAULT_SOURCE
PUBLIC_DOMAIN_STATUS = "public-domain-worldwide"
LICENSE_NOTE = (
    "F. Max Müller (d. 1900), The Dhammapada, Sacred Books of the East "
    "Vol. X Part I, Oxford 1881. Public domain worldwide. Digital text "
    "transcribed from Project Gutenberg ebook #2017; no Project Gutenberg "
    "header or trademark text is redistributed."
)

ROMAN = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8,
    "IX": 9, "X": 10, "XI": 11, "XII": 12, "XIII": 13, "XIV": 14, "XV": 15,
    "XVI": 16, "XVII": 17, "XVIII": 18, "XIX": 19, "XX": 20, "XXI": 21,
    "XXII": 22, "XXIII": 23, "XXIV": 24, "XXV": 25, "XXVI": 26,
}

# Empty retrieval-metadata template. The labeler fills these; the validator
# (validate.py) treats a seed row as "unlabeled" while these are empty.
RETRIEVAL_TEMPLATE = {
    "themes": [],
    "useWhen": [],
    "avoidWhen": [],
    "tone": None,
    "summary": None,
    "emotionalFit": [],
    "vulnerableStatesToAvoid": [],
    "riskNotes": None,
    "excludeOnCrisis": False,
    "labeledBy": None,
    "labeledAt": None,
    "promptVersion": None,
    "reviewedBy": None,
}


def load_source(source: str) -> str:
    if re.match(r"^https?://", source):
        req = urllib.request.Request(source, headers={"User-Agent": "dhp-seed/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")
    with open(source, encoding="utf-8") as fh:
        return fh.read()


def clean_text(fragment: str) -> str:
    """Strip tags, decode entities, normalize whitespace."""
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    fragment = html.unescape(fragment)
    fragment = fragment.replace("—", "—")
    return re.sub(r"\s+", " ", fragment).strip()


def parse_chapter_heading(text: str):
    """'Chapter I. The Twin-Verses' -> (1, 'The Twin-Verses') or None."""
    m = re.match(r"^Chapter\s+([IVXLC]+)\.\s*(.+)$", text)
    if not m:
        return None
    roman, title = m.group(1), m.group(2).strip()
    if roman not in ROMAN:
        return None
    return ROMAN[roman], title


def iter_blocks(raw: str):
    """Yield ('h2'|'p', cleaned_text) in document order."""
    for m in re.finditer(r"<(h2|p)\b[^>]*>(.*?)</\1>", raw, re.S | re.I):
        yield m.group(1).lower(), clean_text(m.group(2))


def parse(raw: str):
    """Return list of {chapterNumber, chapter, verses:[int], text}."""
    passages = []
    cur_num, cur_title = None, None
    for tag, text in iter_blocks(raw):
        if tag == "h2":
            head = parse_chapter_heading(text)
            if head:
                cur_num, cur_title = head
            continue
        # tag == 'p'; a verse paragraph starts with "N." or "N, M."
        m = re.match(r"^(\d+(?:\s*,\s*\d+)*)\.\s+(.*)$", text)
        if not m:
            continue  # anchors, notes, non-verse paragraphs
        verses = [int(n) for n in re.findall(r"\d+", m.group(1))]
        body = m.group(2).strip()
        if not body or cur_num is None:
            continue
        passages.append({
            "chapterNumber": cur_num,
            "chapter": cur_title,
            "verses": verses,
            "text": body,
        })
    return passages


def build_rows(passages, grouping: str):
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    rows = []

    def base(start_verse, chapter_num, chapter_title, text, ref, label, end_verse=None):
        row = {
            "id": f"dhp-{start_verse:03d}",
            "tradition": "buddhist",
            "source": "Dhammapada",
            "chapter": chapter_title,
            "chapterNumber": chapter_num,
            "verseNumber": start_verse,
            "passageRef": ref,
            "displayLabel": label,
            "text": text,
            "translator": TRANSLATOR,
            "sourceUrl": SOURCE_URL,
            "publicDomainStatus": PUBLIC_DOMAIN_STATUS,
            "licenseNote": LICENSE_NOTE,
        }
        if end_verse is not None:
            row["verseNumberEnd"] = end_verse
        row.update({k: (v if not isinstance(v, list) else list(v))
                    for k, v in RETRIEVAL_TEMPLATE.items()})
        return row

    for p in passages:
        verses = p["verses"]
        if grouping == "verse":
            for v in verses:
                ref = f"Dhammapada {v}"
                rows.append(base(v, p["chapterNumber"], p["chapter"], p["text"], ref, ref))
        else:  # passage mode
            start, end = verses[0], verses[-1]
            if start == end:
                ref = f"Dhammapada {start}"
                rows.append(base(start, p["chapterNumber"], p["chapter"], p["text"], ref, ref))
            else:
                ref = f"Dhammapada {start}-{end}"
                rows.append(base(start, p["chapterNumber"], p["chapter"], p["text"],
                                 ref, ref, end_verse=end))
    # seed metadata wrapper
    return {
        "seededAt": now,
        "grouping": grouping,
        "source": SOURCE_URL,
        "translator": TRANSLATOR,
        "rowCount": len(rows),
        "verseCoverage": sorted({v for p in passages for v in p["verses"]}),
        "rows": rows,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=DEFAULT_SOURCE,
                    help="URL or local path to PG #2017 HTML")
    ap.add_argument("--grouping", choices=["passage", "verse"], default="passage")
    ap.add_argument("--out", default="outputs/catalog.seed.json")
    ap.add_argument("--sample", type=int, default=0,
                    help="print first N rows to stderr for inspection")
    args = ap.parse_args(argv)

    raw = load_source(args.source)
    passages = parse(raw)
    covered = sorted({v for p in passages for v in p["verses"]})
    missing = sorted(set(range(1, 424)) - set(covered))
    if missing:
        print(f"WARNING: missing verse numbers: {missing}", file=sys.stderr)
    if covered and covered[-1] != 423:
        print(f"WARNING: max verse is {covered[-1]}, expected 423", file=sys.stderr)

    catalog = build_rows(passages, args.grouping)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(catalog, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print(f"parsed {len(passages)} paragraphs covering {len(covered)} verses "
          f"(1..{covered[-1] if covered else '?'})", file=sys.stderr)
    print(f"wrote {catalog['rowCount']} rows ({args.grouping} mode) -> {args.out}",
          file=sys.stderr)
    for row in catalog["rows"][:args.sample]:
        print(json.dumps({k: row[k] for k in
                          ("id", "passageRef", "chapterNumber", "chapter", "text")},
                         ensure_ascii=False), file=sys.stderr)


if __name__ == "__main__":
    main()
