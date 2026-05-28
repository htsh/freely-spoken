## Labeled-output schema (task 2.4b)

This defines the exact JSON contract each labeling pass must return. It is narrower than the full catalog row in `catalog-schema.md`: a single pass returns only the fields it owns, keyed by `id` so the tool can merge passes back onto the seed row. Canonical fields and provenance are never returned by the model — the tool carries canonical fields through from the seed and writes provenance itself.

The machine-checkable form of the merged labeled row is emitted by `tools/dhammapada-labeling/validate.py --dump-schema` (derived live from `vocabulary.json`, so it cannot drift). This document is the human contract the prompts (task 2.5) implement.

## Ownership map

| Field | Produced by | Notes |
|---|---|---|
| canonical (`id`, `text`, `passageRef`, …) | seed (`seed_catalog.py`) | model never emits or edits these |
| `themes`, `summary`, `emotionalFit`, `useWhen` | **Pass 1 (semantic)** | |
| `tone`, `avoidWhen`, `vulnerableStatesToAvoid`, `riskNotes` | **Pass 2 (safety/tone)** | |
| `labeledBy`, `labeledAt`, `promptVersion` | labeling tool | written per row at merge time |
| `excludeOnCrisis`, `reviewedBy` | human review (task 2.8) | model leaves `excludeOnCrisis=false`, `reviewedBy=null` |

## Pass 1 — semantic output

The model receives one passage (`id`, `passageRef`, `chapter`, `text`) and returns exactly:

```json
{
  "id": "dhp-005",
  "themes": ["non-hatred", "anger"],
  "summary": "Hatred is never ended by more hatred; it ends through love.",
  "emotionalFit": ["anger", "frustration"],
  "useWhen": ["anger", "resentment", "conflict", "reactivity"]
}
```

Constraints (enforced by `validate.py`):

- `id` MUST equal the passage's id (echo, not invent).
- `themes`: 1–4 values, all from `vocabulary.themes`.
- `useWhen`: 1–5 values, all from `vocabulary.useWhen`.
- `emotionalFit`: 1–5 values, all from `vocabulary.emotionalFit` (the device's 14 emotions).
- `summary`: 1–2 sentences, plain modern English, MUST NOT reproduce canonical wording.
- No extra keys. No prose outside the JSON object.

## Pass 2 — safety/tone output

The model receives the same passage (and MUST NOT see Pass 1 output) and returns exactly:

```json
{
  "id": "dhp-005",
  "tone": "gentle",
  "avoidWhen": ["fresh-grief", "abuse-disclosure", "victim-of-relational-harm"],
  "vulnerableStatesToAvoid": ["fresh-grief", "abuse-disclosure"],
  "riskNotes": "Could read as 'be the bigger person' and invalidate someone describing harm done to them."
}
```

Constraints (enforced by `validate.py`):

- `id` MUST equal the passage's id.
- `tone`: exactly one value from `vocabulary.tone`.
- `avoidWhen`: 0–N values from `vocabulary.avoidWhen` (empty allowed for safe-anywhere passages).
- `vulnerableStatesToAvoid`: MUST be a subset of this row's `avoidWhen`, drawn from the crisis-adjacent set (see `labeling-rubric.md`).
- `riskNotes`: free text, may be empty string; MUST NOT quote canonical text.
- No extra keys. No prose outside the JSON object.

## Merge + provenance

The tool merges Pass 1 + Pass 2 onto the seed row by `id` and stamps:

```json
{
  "labeledBy": "<provider>/<model>",
  "labeledAt": "<UTC ISO 8601 at merge time>",
  "promptVersion": "<rubric+prompt version, e.g. labeling-v1.0>",
  "excludeOnCrisis": false,
  "reviewedBy": null
}
```

A row is only considered **labeled** once both passes have merged. Partial rows (one pass only) are invalid for release and are caught by `validate.py --require-labeled`.

## Malformed-output handling (labeling time)

The labeling tool (not the runtime adapter) handles model misbehavior on a pass:

- Non-JSON / trailing prose → strip to first JSON object; if still unparseable, mark the row failed and retry per the tool's retry policy (task 3.2).
- Out-of-vocabulary value → fail the row; do not silently coerce. Out-of-vocab is a labeling-quality signal worth seeing.
- Echoed `id` mismatch → fail the row (prevents cross-contamination in batch runs).
- Canonical text appearing in `summary`/`riskNotes` → fail the row for review.

Runtime malformed-output handling for the *selector* LLM is a separate concern (task 4.3), not covered here.
