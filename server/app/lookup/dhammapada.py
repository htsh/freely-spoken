"""Dhammapada variant adapter (Idle Ashes).

The LLM only ever selects passage IDs from a backend-owned catalog; it never
authors canonical text. Flow (see openspec/changes/dhammapada-catalog-lookup/
adapter-plan.md for the full spec):

  1. Load the catalog (cached at import).
  2. If crisis_flag: hard-exclude high-risk passages BEFORE building the index.
     The LLM is never told a crisis is in progress; it just sees a smaller list.
  3. If crisis leaves < 3 eligible passages: raise LookupUnavailableError.
  4. Deterministic shortlist (top ~45 by additive score) over the eligible set.
  5. LLM picks 1 primary + 2 alternates by ID from the shortlist only.
  6. Validate IDs (exist, in-shortlist, unique) and shortReasons (1-3 sentences,
     no quoted passage text); reject malformed output.
  7. Enrich the 3 chosen IDs with canonical text from the catalog (local, no fetch).
"""

import json
import os
import re

from app.lookup.base import LookupRequest, LookupResult, Reference
from app.llm_runner import AllProvidersFailedError, run as run_llm

_CATALOG_PATH = os.path.join(os.path.dirname(__file__), "dhammapada_catalog.json")
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)

# Frozen crisis hard-exclusion sets — must equal vocabulary.json (v1.0)
# crisisHardExclusion. A test asserts this equality so a vocabulary bump cannot
# silently desync the runtime filter from the labels (adapter-plan.md §4.6).
CRISIS_TONES = frozenset({"stern", "warning"})
CRISIS_THEMES = frozenset({"death", "ascetic-discipline", "moral-rebuke"})
CRISIS_AVOID_WHEN = frozenset({
    "acute-shame", "panic", "despair", "self-blame",
    "abuse-disclosure", "fresh-grief", "suicidal-ideation",
})

SHORTLIST_SIZE = 45
TRANSLATION_LABEL = "F. Max Müller translation (public domain)"


DHAMMAPADA_SYSTEM_PROMPT = """\
You are a Dhammapada passage selector. You are given a person's anonymized emotional situation and a numbered catalog of candidate Dhammapada passages, each with an id and short retrieval metadata (themes, when-useful, tone, summary). Pick the single passage that best fits their situation, plus two strong alternates.

Return a JSON object with exactly this structure:
{
  "primary": {"id": "dhp-XXX", "shortReason": "1-3 sentences"},
  "alternates": [
    {"id": "dhp-XXX", "shortReason": "1-3 sentences"},
    {"id": "dhp-XXX", "shortReason": "1-3 sentences"}
  ]
}

Rules:
- Choose ids ONLY from the provided catalog below. Do not invent ids or use Dhammapada knowledge outside this list.
- Exactly one primary and exactly two alternates. All three ids must be different.
- shortReason: 1-3 sentences, plain modern English, warm but not preachy.
- Do NOT quote, paraphrase, or reproduce the passage text in shortReason. Speak only about why it fits the person's situation.
- Match the passage tone to the person's state. Prefer concrete, compassionate passages. Avoid passages that would sound blaming or harsh for someone who is ashamed, grieving, panicked, despairing, or blaming themselves.
- If several passages fit, prefer the more concrete and gentle one.
"""


# Situation lexicon: lowercase keyword regex -> (useWhen labels, theme labels).
# Human-owned product-tuning data, like the catalog labels; fixture-covered (7.1).
_SITUATION_LEXICON: list[tuple[re.Pattern, list[str], list[str]]] = [
    (re.compile(r"angry|anger|furious|rage|irritat"), ["anger", "reactivity"], ["anger"]),
    (re.compile(r"resent|grudge|bitter"), ["resentment"], ["ill-will"]),
    (re.compile(r"said|regret saying|shouldn'?t have said|spoke"), ["speech-regret"], ["speech"]),
    (re.compile(r"crav|desire|can'?t stop wanting|addict"), ["craving"], ["craving"]),
    (re.compile(r"worry|worried|anxious|anxiety|nervous"), ["worry", "restlessness"], []),
    (re.compile(r"overthink|rumin|can'?t stop thinking|same thought|loop"), ["rumination"], ["mind"]),
    (re.compile(r"argument|fight|fought|conflict|clash"), ["conflict"], []),
    (re.compile(r"hurt by|betrayed|let down by|cheated"), ["relational-hurt"], []),
    (re.compile(r"hopeless|discourag|giving up|pointless|no use"), ["discouragement"], []),
    (re.compile(r"proud|better than|superior|arrogan"), ["pride"], ["pride"]),
    (re.compile(r"confused|lost|don'?t know|unsure"), ["confusion", "doubt"], []),
    (re.compile(r"grateful|thankful|blessed"), ["gratitude"], []),
    (re.compile(r"restless|can'?t sit still|agitated|on edge"), ["restlessness"], []),
    (re.compile(r"envy|jealous"), ["envy"], []),
    (re.compile(r"impatient|patience"), ["patience-needed"], []),
]

# Vulnerable-state lexicon: feeds the soft (non-crisis) avoidWhen penalty.
_VULNERABLE_LEXICON: list[tuple[re.Pattern, str]] = [
    (re.compile(r"ashamed|embarrass|humiliat"), "acute-shame"),
    (re.compile(r"my fault|blame myself|i ruined|i messed"), "self-blame"),
    (re.compile(r"panic|can'?t breathe|terrified"), "panic"),
    (re.compile(r"hopeless|no point|despair"), "despair"),
    (re.compile(r"grief|grieving|just lost|passed away|died"), "fresh-grief"),
    (re.compile(r"abused|he hit|she hit|assault|beat me"), "abuse-disclosure"),
]

# useWhen values that coincide with the emotionalFit/device-emotion vocabulary,
# so a matching emotion also scores a useWhen hit.
_USEWHEN_VOCAB = {
    "anger", "resentment", "reactivity", "speech-regret", "craving", "envy",
    "restlessness", "worry", "rumination", "conflict", "relational-hurt",
    "discouragement", "pride", "confusion", "doubt", "gratitude", "contentment",
    "equanimity", "joy", "patience-needed", "generosity-impulse", "complacency",
}


class DhammapadaAdapterError(Exception):
    """Raised when LLM output is malformed enough to be unusable."""


class LookupUnavailableError(Exception):
    """Crisis hard-exclusion left fewer than three eligible passages.

    The HTTP layer maps this to a structured lookup_unavailable response rather
    than relaxing the filter or substituting generated content (adapter-plan.md §4.8).
    """


def _load_catalog() -> tuple[list[dict], dict[str, dict]]:
    with open(_CATALOG_PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    rows = data["rows"]
    by_id = {r["id"]: r for r in rows}
    return rows, by_id


_CATALOG, _CATALOG_BY_ID = _load_catalog()


def _excluded(row: dict) -> bool:
    """Crisis hard-exclusion predicate (adapter-plan.md §4.6 / vocabulary.json)."""
    return (
        row["tone"] in CRISIS_TONES
        or any(t in CRISIS_THEMES for t in row["themes"])
        or any(a in CRISIS_AVOID_WHEN for a in row["avoidWhen"])
        or bool(row.get("excludeOnCrisis"))
    )


def _eligible(crisis_flag: bool) -> list[dict]:
    if not crisis_flag:
        return _CATALOG
    return [r for r in _CATALOG if not _excluded(r)]


def _derive_signals(req: LookupRequest) -> tuple[set[str], set[str], set[str]]:
    """Map the request onto (useWhen hits, theme hits, vulnerable states)."""
    text = req.anonymized_text.lower()
    emotions = {e.strip().lower() for e in req.emotions}

    usewhen: set[str] = set(emotions & _USEWHEN_VOCAB)
    themes: set[str] = set()
    for pat, uw, th in _SITUATION_LEXICON:
        if pat.search(text):
            usewhen.update(uw)
            themes.update(th)

    vulnerable: set[str] = set()
    for pat, state in _VULNERABLE_LEXICON:
        if pat.search(text):
            vulnerable.add(state)

    return usewhen, themes, vulnerable


def _shortlist(eligible: list[dict], req: LookupRequest) -> list[dict]:
    usewhen, themes, vulnerable = _derive_signals(req)
    emotions = {e.strip().lower() for e in req.emotions}

    def score(r: dict) -> int:
        s = 3 * len(emotions & set(r["emotionalFit"]))
        s += 2 * len(usewhen & set(r["useWhen"]))
        s += len(themes & set(r["themes"]))
        s -= 4 * len(vulnerable & set(r["avoidWhen"]))
        if r["tone"] in CRISIS_TONES:
            s -= 1
        return s

    # Stable: higher score first, then ascending id. Top SHORTLIST_SIZE.
    ranked = sorted(eligible, key=lambda r: (-score(r), r["id"]))
    return ranked[:SHORTLIST_SIZE]


def _index_block(shortlist: list[dict]) -> str:
    lines = []
    for r in shortlist:
        lines.append(
            f"{r['id']} | themes: {', '.join(r['themes'])} "
            f"| useWhen: {', '.join(r['useWhen'])} "
            f"| tone: {r['tone']} | {r['summary']}"
        )
    return "\n".join(lines)


def _user_prompt(req: LookupRequest, shortlist: list[dict]) -> str:
    return (
        f"Anonymized situation: {req.anonymized_text}\n"
        f"Sentiment: {req.sentiment}\n"
        f"Emotions: {', '.join(req.emotions)}\n\n"
        f"Candidate passages:\n{_index_block(shortlist)}"
    )


def _extract_json(text: str) -> str:
    """Brace-matched JSON extraction tolerant of prose/code fences.

    Ported from christian.py — kept local to avoid coupling to that adapter's
    internals; the two may diverge as the variants' prompts diverge.
    """
    text = text.strip()
    match = _JSON_FENCE_RE.search(text)
    if match:
        text = match.group(1).strip()

    start = text.find("{")
    if start == -1:
        return ""

    depth = 0
    in_string = False
    escape = False
    for i, ch in enumerate(text[start:], start=start):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if not in_string:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
    return text[start:]


def _normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", s.lower())


def _looks_like_quotation(short_reason: str, passage_text: str) -> bool:
    """True if shortReason appears to reproduce the passage (adapter-plan.md §4.3)."""
    if re.search(r'"[^"]{60,}"', short_reason):
        return True
    reason_words = _normalize(short_reason).split()
    passage_norm = " " + " ".join(_normalize(passage_text).split()) + " "
    for i in range(len(reason_words) - 7):
        shingle = " ".join(reason_words[i : i + 8])
        if f" {shingle} " in passage_norm:
            return True
    return False


def _validate_entry(data: dict, label: str, allowed_ids: set[str]) -> str:
    if "id" not in data or "shortReason" not in data:
        raise DhammapadaAdapterError(f"Missing id or shortReason in {label}: {data}")

    pid = data["id"]
    if pid not in _CATALOG_BY_ID:
        raise DhammapadaAdapterError(f"Nonexistent id in {label}: {pid}")
    if pid not in allowed_ids:
        # Excluded (crisis) or not shortlisted: same rejection path as nonexistent.
        raise DhammapadaAdapterError(f"id not in candidate set in {label}: {pid}")

    short_reason = data["shortReason"]
    sentences = [s.strip() for s in short_reason.split(".") if s.strip()]
    if len(sentences) < 1 or len(sentences) > 3:
        raise DhammapadaAdapterError(
            f"shortReason must be 1-3 sentences in {label}: {short_reason}"
        )
    if _looks_like_quotation(short_reason, _CATALOG_BY_ID[pid]["text"]):
        raise DhammapadaAdapterError(
            f"shortReason appears to quote the passage in {label}: {short_reason}"
        )
    return pid


def _to_reference(data: dict) -> Reference:
    row = _CATALOG_BY_ID[data["id"]]
    return Reference(
        ref=row["displayLabel"],
        shortReason=data["shortReason"],
        text=row["text"],
        translation=TRANSLATION_LABEL,
    )


class DhammapadaAdapter:
    app_variant = "dhammapada"

    async def select(self, req: LookupRequest) -> LookupResult:
        eligible = _eligible(req.crisis_flag)
        if req.crisis_flag and len(eligible) < 3:
            raise LookupUnavailableError(
                f"crisis exclusion left {len(eligible)} eligible passages"
            )

        shortlist = _shortlist(eligible, req)
        allowed_ids = {r["id"] for r in shortlist}

        llm = await run_llm(DHAMMAPADA_SYSTEM_PROMPT, _user_prompt(req, shortlist))

        stripped = _extract_json(llm.text)
        if not stripped:
            raise DhammapadaAdapterError(
                f"LLM returned empty/unparseable response. Raw: {llm.text[:200]!r}"
            )
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError as e:
            raise DhammapadaAdapterError(
                f"Invalid JSON from {llm.provider}: {e}\nStripped: {stripped[:500]!r}"
            ) from e

        if "primary" not in data or "alternates" not in data:
            raise DhammapadaAdapterError(f"Missing primary or alternates: {data}")
        alternates_data = data["alternates"]
        if not isinstance(alternates_data, list) or len(alternates_data) != 2:
            raise DhammapadaAdapterError(
                f"Expected exactly 2 alternates, got: {alternates_data}"
            )

        primary_id = _validate_entry(data["primary"], "primary", allowed_ids)
        alt_ids = [
            _validate_entry(a, f"alternate[{i}]", allowed_ids)
            for i, a in enumerate(alternates_data)
        ]
        if len({primary_id, *alt_ids}) != 3:
            raise DhammapadaAdapterError(
                f"Duplicate ids across primary/alternates: {[primary_id, *alt_ids]}"
            )

        return LookupResult(
            primary=_to_reference(data["primary"]),
            alternates=[_to_reference(a) for a in alternates_data],
            provider=llm.provider,
            model=llm.model,
            retry_count=llm.retry_count,
            fallback_used=llm.fallback_used,
        )


__all__ = [
    "DhammapadaAdapter",
    "DhammapadaAdapterError",
    "LookupUnavailableError",
    "AllProvidersFailedError",
]
