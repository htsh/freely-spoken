## Dhammapada labeling rubric (task 2.4a)

This rubric defines what each LLM-labeled field means, how to judge it, and what correct vs incorrect labels look like. It is the human-authored judgment layer the labeling prompts (task 2.5) operationalize. All vocabulary-constrained values come from the frozen `vocabulary.json` (v1.0); this rubric never introduces a value not in that file.

The labeler sees, per passage: `id`, `passageRef`, `chapter`, and canonical `text`. It never edits canonical fields. It produces retrieval metadata only.

## Guiding objective

Labels exist to power one decision: *given an anonymized user situation, is this passage a good, safe thing to show?* Optimize for matching usefulness and harm-avoidance, **not** for academic Buddhist taxonomy. A label that is scripturally precise but useless for matching is a wrong label here.

Two failure modes to weigh equally:

- **Miss** — passage that would genuinely help is not surfaced because its labels are too narrow.
- **Harm** — passage that stings (blame, sternness, mortality, renunciation-pressure) is surfaced to someone fragile because its safety labels are too generous.

When uncertain on a safety label, label *more* cautiously (wider `avoidWhen`). When uncertain on a semantic label, label *truthfully* to the text, not aspirationally.

## Two passes

Per `design.md`, labeling is two prompts so semantic fit and safety/tone do not blur:

- **Pass 1 — semantic:** `themes`, `summary`, `emotionalFit`, `useWhen`
- **Pass 2 — safety/tone:** `tone`, `avoidWhen`, `vulnerableStatesToAvoid`, `riskNotes`

`excludeOnCrisis` and `reviewedBy` are **never** set by the labeler — they are human-review-only (task 2.8). Provenance (`labeledBy`, `labeledAt`, `promptVersion`) is written by the tool, not the model.

---

## Pass 1 — semantic fields

### `themes` (1–4 values from `vocabulary.themes`)

What the verse is *about*. Pick the dominant subjects, most-central first.

- Judge by the verse's actual content, not the chapter title. A verse in "The Flowers" chapter may be about `heedlessness`, not flowers.
- Prefer 1–2 strong themes over 4 weak ones. Four is a ceiling for genuinely multi-topic verses, not a target.
- Use crisis-flagged themes (`death`, `ascetic-discipline`, `moral-rebuke`) **only when truly central** — they trigger hard exclusion, so over-applying them needlessly shrinks the crisis-time index.

**Correct** — DhP 5 ("hatred does not cease by hatred at any time… by love alone"): `["non-hatred", "anger"]`.
**Incorrect** — same verse tagged `["virtue", "wisdom", "peace", "conduct"]`: vague, dilutes the strong `non-hatred` signal, hits the cap with filler.

### `summary` (1–2 sentences, plain modern English)

A compact paraphrase the selector reads instead of the (dated) canonical text.

- Modern, neutral, literal. No Victorian phrasing, no embellishment, no second-person preaching.
- **Must not reproduce canonical translation wording** — it is retrieval metadata, not displayable scripture. Paraphrase, don't quote.
- One idea, stated plainly.

**Correct** — DhP 1: "Our experience is shaped by the mind; act or speak from an unwholesome mind and suffering follows."
**Incorrect** — "All that we are is the result of what we have thought" (this is near-verbatim Müller — that is canonical text leaking into metadata).

### `emotionalFit` (1–5 values from `vocabulary.emotionalFit` — the device's 14 emotions)

The user *emotions* this passage speaks to. These are matched directly against the `emotions` array the device sends, so use the device's words exactly.

- Pick emotions a person feeling them would find this passage *relevant* to — not the emotion the verse depicts.
- It is fine for a calm, instructive verse to fit agitated emotions (`anger`, `frustration`, `anxiety`) if it offers them something.

**Correct** — DhP 5: `["anger", "frustration"]` (someone angry/bitter is who this helps).
**Incorrect** — DhP 5: `["peace", "love"]` (the verse mentions love, but someone already at peace is not who needs it — this mislabels depicted content as fit).

### `useWhen` (1–5 values from `vocabulary.useWhen`)

Situational states where surfacing this passage helps. Richer than `emotionalFit` — includes situations (`conflict`, `speech-regret`, `complacency`) the device's emotion list can't express.

- Concrete situations beat abstract virtues. `rumination` is more useful than implying "whenever someone should think well."
- Do not list a state in both `useWhen` and `avoidWhen`. If a passage helps anger but harms someone enraged at an abuser, that nuance lives in `avoidWhen` / `vulnerableStatesToAvoid`, not by contradicting `useWhen`.

**Correct** — DhP 5: `["anger", "resentment", "conflict", "reactivity"]`.
**Incorrect** — DhP 5: `["fresh-grief"]` (not a useWhen value at all — that is an avoidWhen state; category error).

---

## Pass 2 — safety / tone fields

Pass 2 runs without seeing Pass 1's output, judging the same canonical text for how it *lands*, especially on a fragile reader.

### `tone` (exactly 1 value from `vocabulary.tone`)

The felt tone of the passage as a vulnerable modern reader would experience it — not the translator's intent.

- `stern` and `warning` are the two crisis-hard-exclusion tones. Apply them honestly: a verse that frames wrongdoing and punishment (e.g. DhP 17, "the evil-doer suffers… he suffers more when gone on the evil path") is `warning` or `stern`, and labeling it `direct` to keep it eligible would defeat the safety design.
- Reserve `gentle` for genuinely consoling verses. Most Dhammapada verses are `direct`, `aphoristic`, or `exhortative`; do not inflate `gentle`.

**Correct** — DhP 5: `gentle`. DhP 1: `direct`. DhP 17 (evildoer suffers here and hereafter): `warning`.
**Incorrect** — DhP 17 labeled `contemplative` (launders a threatening verse past the crisis filter).

### `avoidWhen` (0–N values from `vocabulary.avoidWhen`)

States where this passage may be unhelpful, invalidating, or harmful. Empty array allowed for genuinely safe-anywhere verses.

- Think about who would be *hurt*, not just unmoved. A verse on consequences/responsibility can read as blame to someone in `acute-shame` or `self-blame`.
- A verse mentioning death or impermanence belongs in `fresh-grief` avoid even if gently meant.
- A verse about meeting hatred with non-hatred can sting a `victim-of-relational-harm` or someone in `rage-at-aggressor` (it can read as "be the bigger person" to someone freshly wronged).
- Err wide. A false `avoidWhen` costs one missed match; a missing one risks harm.

**Correct** — DhP 5: `["fresh-grief", "abuse-disclosure", "victim-of-relational-harm"]` (non-hatred can invalidate the freshly harmed).
**Incorrect** — DhP 5: `[]` (ignores that "answer hatred with love" wounds someone describing abuse).

### `vulnerableStatesToAvoid` (subset of this row's `avoidWhen`)

**Resolution of the open question (was flagged in `vocabulary.md`):** `vulnerableStatesToAvoid` is the *acute-harm subset* of `avoidWhen` — the states where surfacing the passage is not merely unhelpful but actively risky for a fragile person. It is **not** a parallel free list.

- **Invariant:** every value here MUST also appear in this row's `avoidWhen`. The validator (task 2.7) enforces `vulnerableStatesToAvoid ⊆ avoidWhen`.
- The labeler populates it as the intersection of `avoidWhen` with the crisis-adjacent vulnerable set: `acute-shame`, `panic`, `despair`, `self-blame`, `abuse-disclosure`, `fresh-grief`, `suicidal-ideation`.
- Human review (task 2.8) may add a state here the labeler under-weighted — but must also ensure it is in `avoidWhen` to preserve the invariant.
- Distinct role vs `avoidWhen`: `avoidWhen` is the full caution list driving normal shortlist exclusion; `vulnerableStatesToAvoid` is the high-severity flag that prioritizes human review and serves as defense-in-depth alongside the crisis hard-exclusion logic.

**Correct** — DhP 5 with `avoidWhen = ["fresh-grief", "abuse-disclosure", "victim-of-relational-harm"]` → `vulnerableStatesToAvoid = ["fresh-grief", "abuse-disclosure"]` (the two crisis-adjacent ones; `victim-of-relational-harm` is a caution but not in the crisis-adjacent set).
**Incorrect** — `vulnerableStatesToAvoid = ["panic"]` when `panic` is not in `avoidWhen` (violates the subset invariant).

### `riskNotes` (free text, may be empty)

One sentence, reviewer-facing, on *why* this passage could hurt and to whom. Not used by the selector; it is a human-review aid.

**Correct** — DhP 5: "Could read as 'be the bigger person' and invalidate someone describing harm done to them."
**Incorrect** — quoting the verse, or restating `avoidWhen` as a list with no reasoning.

---

## Cross-field consistency rules (validator-checkable)

1. No state appears in both `useWhen` and `avoidWhen` of the same row.
2. `vulnerableStatesToAvoid ⊆ avoidWhen`.
3. `summary` shares no long verbatim span with canonical `text` (paraphrase check; soft, flagged for review).
4. Cardinalities: `themes` 1–4, `useWhen` 1–5, `emotionalFit` 1–5, `tone` exactly 1.
5. All values drawn only from `vocabulary.json` v1.0.

## High-risk review triggers (feed task 2.8)

A row is routed to mandatory human review if its generated labels include any of: a crisis-hard-exclusion `tone` (`stern`, `warning`); a crisis-hard-exclusion `theme` (`death`, `ascetic-discipline`, `moral-rebuke`); any crisis-adjacent value in `avoidWhen`/`vulnerableStatesToAvoid`; or non-empty `vulnerableStatesToAvoid`. These are the passages where a bad label does the most damage.

## Revision loop (task 2.9)

If fixture testing (tasks 7.1–7.2) shows systematic mismatch or unsafe tone, revise *this rubric* and bump `promptVersion`, then regenerate the affected rows — do not hand-patch individual fields disconnected from the rubric. Per-row provenance makes targeted regeneration possible.
