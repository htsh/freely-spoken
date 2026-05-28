## Dhammapada catalog schema (tasks 2.1, 2.2)

This document is the planning artifact for the Dhammapada catalog schema and storage choice. It is the source of truth that the labeling tool (task 3.1), the validation script (task 2.7), and the runtime adapter (task 5.1+) all derive from. Controlled-vocabulary enums for every constrained field live in `vocabulary.json` and are explained in `vocabulary.md`.

## 2.2 Storage

The first pass uses a single checked-in JSON file loaded into memory by FastAPI at startup. Rationale lives in `design.md` "Storage Decision":

- 423 records is tiny.
- No runtime dependency.
- Reviewable in pull requests.
- Testable with the validation script.
- Runs on the small VPS class the rest of `server/` targets.

Mongo is acceptable later if catalog editing/review needs an admin workflow. Qdrant or other vector stores are out of scope per `design.md` "Deferred: vector search."

**Path:** `server/app/lookup/dhammapada_catalog.json` (final location; lands with task 5.2).

## 2.1 Schema

Every catalog row is one JSON object with the following fields. Field grouping reflects the canonical-vs-retrieval boundary that the spec requires (`dhammapada-lookup-flow` Requirement: "retrieval metadata SHALL be stored separately from canonical passage text"). Storage is one object per row; the grouping is conceptual.

### Canonical content

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | Stable opaque ID. Pattern: `dhp-NNN` zero-padded to 3 digits (`dhp-001` … `dhp-423`). Never reused; never reordered. |
| `tradition` | string enum | yes | Always `"buddhist"` for this catalog. Distinguishes from future variant catalogs. |
| `source` | string enum | yes | Always `"Dhammapada"` for this catalog. |
| `chapter` | string | yes | Chapter title in the chosen translation (e.g. `"The Twin Verses"`). |
| `chapterNumber` | integer | yes | 1-indexed chapter number (1–26). |
| `verseNumber` | integer | yes | 1-indexed verse number within the corpus (1–423). |
| `passageRef` | string | yes | Display reference (e.g. `"Dhammapada 1"`). |
| `displayLabel` | string | yes | UI label. For v1, equals `passageRef`. Reserved separate to allow chapter-title styling later without re-keying. |
| `text` | string | yes | Canonical verse text. Sourced from Project Gutenberg #2017 (Müller, 1881). Whitespace-normalized. May contain multi-line breaks for paired verses. |

### Provenance and rights

All four fields below come from `rights-review.md` and are identical for every Müller-sourced row in v1. They are stored per-row anyway so the catalog stays self-describing if a later translation is mixed in.

| Field | Type | Required | Value for v1 |
|---|---|---|---|
| `translator` | string | yes | `"F. Max Müller"` |
| `sourceUrl` | string | yes | `"https://www.gutenberg.org/files/2017/2017-h/2017-h.htm"` |
| `publicDomainStatus` | string enum | yes | `"public-domain-worldwide"` |
| `licenseNote` | string | yes | The license summary from `rights-review.md` § 1.3. |

### Retrieval metadata

These fields are LLM-generated under the labeling rubric and human-reviewed. They are never displayed as user-facing passage content. Vocabulary-constrained fields draw from `vocabulary.json`.

| Field | Type | Required | Notes |
|---|---|---|---|
| `themes` | array<string> | yes | 1–4 values from `vocabulary.themes`. |
| `useWhen` | array<string> | yes | 1–5 values from `vocabulary.useWhen`. User states this passage is helpful for. |
| `avoidWhen` | array<string> | yes (may be empty) | Values from `vocabulary.avoidWhen`. User states where this passage may harm. Empty array allowed for clearly safe passages. |
| `tone` | string enum | yes | One value from `vocabulary.tone`. |
| `summary` | string | yes | 1–2 sentences. Compact paraphrase the selector reads. Must not be canonical translation text. |
| `emotionalFit` | array<string> | yes | 1–5 values from `vocabulary.emotionalFit`. **Drawn from the exact 14-emotion vocabulary the device emits** (see `hooks/sentiment-utils.ts`), so the shortlist heuristic (task 4.4a) can compare directly. |
| `vulnerableStatesToAvoid` | array<string> | yes (may be empty) | Values from `vocabulary.vulnerableStatesToAvoid`. Subset of `avoidWhen` specifically used by reviewers to mark states where this passage would harm a vulnerable user. See `vocabulary.md` for the relationship to `avoidWhen`. |
| `riskNotes` | string | yes (may be empty) | Free-text reviewer-readable notes on tone risk. Not used by the selector. |
| `excludeOnCrisis` | boolean | yes | Per-row reviewer flag. `true` hard-excludes the passage when `crisisFlag = true`, even if categorical filters would not have caught it. Default `false`. Only set during human review (task 2.8). |

### Per-row labeling provenance

These fields document which run produced or reviewed each row so partial relabeling can target only the affected rows after a rubric revision (resolved decision: "Per-row labeling provenance added to the schema").

| Field | Type | Required | Notes |
|---|---|---|---|
| `labeledBy` | string | yes | Provider/model identifier (e.g. `"fireworks/llama-3.1-70b-instruct"`). |
| `labeledAt` | string (ISO 8601) | yes | UTC timestamp the row was labeled. |
| `promptVersion` | string | yes | Identifier for the labeling prompt + rubric version (e.g. `"labeling-v1.0"`). |
| `reviewedBy` | string \| null | yes | `null` until human review. After review: `"<reviewer-handle>@<YYYY-MM-DD>"`. |

## Validation invariants

These get enforced by the validation script in task 2.7. Listing them here so they are not lost between artifacts.

- `id` matches `^dhp-\d{3}$` and is unique across the catalog.
- `verseNumber` is unique across the catalog and falls in 1..423.
- `chapterNumber` falls in 1..26.
- All vocabulary-constrained fields contain only values present in `vocabulary.json`.
- `themes` has at least 1 entry and at most 4.
- `useWhen` has at least 1 entry and at most 5.
- `emotionalFit` has at least 1 entry and at most 5.
- `text`, `summary`, `translator`, `sourceUrl`, `publicDomainStatus`, `licenseNote`, `labeledBy`, `promptVersion` are non-empty strings.
- `labeledAt` parses as ISO 8601.
- `excludeOnCrisis` is a boolean.
- Canonical fields (`text`, `passageRef`, `translator`, etc.) never contain LLM-generated content; this is enforced by the labeling tool refusing to write to those fields.

## Out of scope for this artifact

- Field-by-field labeling rubric (task 2.4a — next session).
- JSON Schema document for labeled-output validation (task 2.4b — next session).
- Two-pass labeling prompts (task 2.5).
- Validation script implementation (task 2.7).
- The catalog file itself (task 2.3 — transcription job, deferred).
