# Idle Ashes — overview

A plain-English walkthrough of the Dhammapada variant, written for the project owner (a programmer, not a data scientist). Read end-to-end in one sitting. The authoritative artifacts are under `openspec/changes/dhammapada-catalog-lookup/`:

- `proposal.md` — what we decided
- `design.md` — how it works
- `tasks.md` — the checklist
- `specs/dhammapada-lookup-flow/spec.md` — testable requirements

This doc is the friendlier version of all four.

## What Idle Ashes is

Idle Ashes is the Buddhist variant of mic-check, parallel to **Freely Spoken** for Christian. Same pipeline:

1. You speak.
2. The phone transcribes and anonymizes the transcript on-device.
3. Only the anonymized text + sentiment metadata leaves the device.
4. The backend picks a Dhammapada passage that fits.
5. The phone shows it (and optionally reads it aloud).

The Dhammapada is a Buddhist text of 423 short verse-form sayings on anger, craving, grief, speech, mindfulness, reactivity, and conduct. That makes it a good fit for the "short, concrete passage" product shape already validated for Christian.

Domain to secure: `idleashes.com`.

## Why this needs more careful prep than Freely Spoken

For Christian, the backend asks Gemini "what Bible verse fits this situation?" and Gemini does fine — it knows Bible references cold. Then the server fetches canonical text from the Bible API. The LLM does selection; the API supplies canonical text.

For Dhammapada that doesn't work cleanly:

- LLMs **do not reliably know exact Dhammapada verse numbers** the way they know Bible references.
- LLMs **make up Dhammapada wording** — there are many translations and the model blends them.
- There's no widely-used "Dhammapada API" with reliable canonical text by verse number.

So we have to build the catalog ourselves. The LLM only picks IDs from a list we hand it; the server returns canonical text from our own catalog. **The LLM never writes a Dhammapada line.**

## The catalog, in one paragraph

A catalog is a JSON file (or in-memory record set) with one row per approved Dhammapada verse. Each row carries:

- The canonical verse text (user-facing).
- Metadata that helps the selector pick the right verse (not user-facing): what's it about, when does it apply, when is it harmful, what tone does it have.

Programmer analogy: it's a product catalog where each row has SKU + description + tags. The LLM sees the tags, picks the SKU; the server fulfills with the description.

## Why "labeling" matters

To pick a verse for a user, the selector needs to match the user's emotional state against each verse's *useful-when* and *unsafe-when* properties. Those properties have to be on every row, consistently.

Hand-tagging 423 verses with a consistent rubric is tedious and easy to do inconsistently. So we use an LLM to write the first draft of the labels. A human (you) defines the rules, reviews the risky outputs, and signs off.

Programmer analogy: imagine annotating 423 functions with typed metadata. You could do it by hand, or write a script that generates a first pass and audit it. We're doing the latter, with the LLM as the script.

## The two passes (and why they're separated)

We run two labeling prompts per verse, not one:

**Pass 1: semantic labels** — what is this verse *about*?
- `themes` — short conceptual tags (e.g. anger, mind, speech)
- `useWhen` — emotional/situational fits (e.g. rumination, conflict, speech regret)
- `summary` — one-sentence plain-English summary
- `emotionalFit` — bucket used for matching

**Pass 2: safety/tone labels** — could this *hurt* someone?
- `tone` — gentle / direct / stern / contemplative / etc. (from a fixed list)
- `avoidWhen` — states where this verse would land badly (e.g. acute shame, fresh grief)
- `vulnerableStatesToAvoid` — explicit user states to flag
- `riskNotes` — free-text caveats for human reviewers

The separation matters. If you ask one prompt "what does this mean AND who might it hurt?", the two judgments contaminate each other — the model softens its semantic read to make tone look safer, or it skips tone because it's busy reading. Splitting them keeps each judgment clean.

## Controlled vocabulary (the unglamorous critical part)

Programmer analogy: enums vs free-form strings.

If labels are free text — say `themes: ["dealing with anger and lashing out"]` — the selector can't filter reliably because every verse uses different wording. So we **freeze the allowed values** for `themes`, `useWhen`, `avoidWhen`, `tone`, `emotionalFit`, and `vulnerableStatesToAvoid` in a checked-in vocabulary file. The labeling prompt is then constrained: "you may only return values from this list."

This is also where the **crisis-flag hard-exclusion vocabulary** gets defined. Some `tone` values (e.g. `stern`) and some `themes` (e.g. death, ascetic-correction, moral-rebuke) get marked as auto-excluded when `crisisFlag = true`. That marking is part of the vocabulary file, not a separate config.

**Lock the vocabulary before drafting any labeling prompts.** Changing the vocabulary later means re-labeling.

## Why we're not using a vector database

You might've seen RAG architectures where you embed every document, store the vectors in Qdrant or pgvector, and let cosine similarity match. We're explicitly **not** doing that for v1.

- 423 records is tiny. Embeddings buy nothing at this size.
- Tone is the hard part, and embeddings don't capture tone well. "This verse is angry-sounding" and "this verse is gentle-sounding" can have similar embeddings if the surface words rhyme.
- Curated metadata under a frozen vocabulary lets a human audit every match decision. Embeddings are opaque.
- One less moving part.

Vector search comes back on the table only if (a) we expand to multiple wisdom corpora at once, or (b) curated labels measurably fail to find good matches.

## How runtime selection works

When a user speaks, the backend:

1. Takes the anonymized text + sentiment + emotions + `crisisFlag` (set by the existing crisis-keyword scan).
2. If `crisisFlag = true`, filters the catalog to remove high-risk passages **before** the LLM sees anything.
3. Builds a deterministic shortlist of 30–60 candidate verses by matching `useWhen` + `themes` against the user's state, excluding `avoidWhen` conflicts.
4. Hands the shortlist (IDs + retrieval metadata, **no canonical text**) to an LLM with a prompt: "pick one primary and two alternates from these."
5. Validates the LLM's chosen IDs (do they exist? are they distinct? were they not crisis-excluded?).
6. Fetches canonical text from the catalog for those IDs.
7. Returns `{ primary, alternates, ... }`.

The LLM never writes passage text. It never knows there's a crisis. It picks from a pre-filtered list.

If the shortlist ever proves to miss good matches, we fall back to handing the LLM the *full* compact index (all 423 rows minus the crisis-excluded ones). That's a measured response, not a default — full-index is slower and more expensive per request.

## Crisis-flag hard exclusion, briefly

Freely Spoken has a crisis-flag: the server scans for crisis-adjacent language (suicidality, panic, etc.) and sets a flag on the response. The flag is informational only; the LLM prompt isn't changed.

For Idle Ashes, informational-only isn't enough. The Dhammapada has passages on death, ascetic discipline, and harsh moral correction that would land badly on a user in acute shame, panic, despair, or fresh grief.

- When `crisisFlag = true`, the catalog/shortlist is filtered to remove passages with stern tone, crisis-adjacent `avoidWhen` values, high-risk themes, or an explicit per-row `excludeOnCrisis` reviewer flag.
- The LLM is **not** told a crisis is in progress. It just gets a smaller, safer list.
- If filtering leaves fewer than three eligible passages, the backend returns `lookup_unavailable` rather than relaxing the filter.

Stricter posture than Freely Spoken. Intentional.

## What you can do now to prepare

Roughly ordered by what unblocks what.

### 1. Pick the translation (blocking everything else)

The main candidates:

- **F. Max Müller** (1881) — public domain, no legal risk, but archaic (*hath*, *thee*). Product feel will be Victorian.
- **Acharya Buddharakkhita** (1985) — modern, widely used, hosted by Buddhist Publication Society (BPS) / Access to Insight. License is more constrained: BPS allows non-commercial reuse with attribution; commercial use needs permission. Verify exact terms before relying on it.
- **Thanissaro Bhikkhu** — modern, Access to Insight, Creative Commons (verify which CC variant).
- **Gil Fronsdal** (Shambhala, 2005) — contemporary and well-regarded but copyright-protected; would need licensing.

Whichever you pick **drives product feel as much as any prompt tuning**. Make it a deliberate choice, not a default to "whatever's public domain."

Once chosen, record: exact edition, source URL, translator, publication date, public-domain or license status, license note.

### 2. Decide: full 423 or curated subset for v1?

Recommendation: **start with a curated subset of 30–50 verses** covering the most common emotional states (anger, rumination, conflict, speech regret, grief, gratitude, restlessness). Ship the end-to-end loop. Then expand.

Doing all 423 first means months of labeling + review before anyone sees a Dhammapada response in the app. A small-subset version lets you ship in weeks, validate the product shape, then scale up labeling with a rubric already battle-tested against real responses.

### 3. Draft the controlled vocabulary

Sit-down-and-think work, no LLM needed. Open a file (likely `tools/dhammapada-labeling/vocabulary.yaml` or similar) and enumerate allowed values for:

- **`themes`** — aim for 20–40. Examples: `anger`, `mind`, `speech`, `craving`, `attention`, `consequences`, `impermanence`. Mark which are crisis-flag hard-exclude (likely: `death`, `ascetic-correction`, `moral-rebuke`).
- **`useWhen`** — emotional/situational triggers. 20–30. Examples: `rumination`, `speech regret`, `reactivity`, `conflict`, `gratitude`, `restlessness`.
- **`avoidWhen`** — danger states. 10–15. Examples: `acute shame`, `panic`, `despair`, `self-blame`, `abuse disclosure`, `fresh grief`, `suicidal ideation`.
- **`tone`** — small enum. Likely: `gentle`, `direct`, `stern`, `contemplative`, `playful`. Mark which are crisis-flag hard-exclude (likely `stern` and any other "harsh" tones you add).
- **`emotionalFit`** — overlaps with `useWhen` by design.
- **`vulnerableStatesToAvoid`** — overlaps with `avoidWhen` by design.

Don't over-engineer. First pass: bias toward fewer values you can keep straight. You can always split a value later.

### 4. Write 10–20 fixture inputs

For evaluating prompt iterations, write concrete inputs and the verses you'd want surfaced. Like:

```
input: "I keep replaying that argument from yesterday and I can't sleep."
sentiment: negative
emotions: rumination, regret
expected verse family: anger / non-hatred / mindfulness
```

These don't need exact verse IDs (you don't have them yet). Just describe what *should* come back. Once labels exist, you can grep for which verses match — and revise the rubric if the matches are bad.

### 5. Inventory available credits

Check what's free or already paid on:

- **Hugging Face Inference** — free tier exists; setting `HF_TOKEN` raises rate limits.
- **Fireworks** — credits often included with new accounts.
- **Replicate** — pay-as-you-go; some free credit for small models.

Labeling is a one-time batch — estimate cost as roughly `423 verses × 2 passes × ~600 input tokens × model price`. Even cautious estimates land in low single dollars for most models.

The labeling model **doesn't have to be the runtime model**. Use the strongest reasonable choice for the offline batch; keep runtime on Gemini Flash free tier.

### 6. Skim adjacent project artifacts

- `docs/stoic-curation-rubric.md` — Stoic is curating now under similar principles. The "Stoic but not bro-Stoic" framing transfers in spirit: tone matters, not every passage fits every state, the rubric is the artifact.
- `docs/architecture-review-2026-05-16.md` — load-bearing review of the current pipeline.
- `docs/other_wisdom_sources.md` — the decision sheet that promoted Dhammapada into the committed v3 slot.
- `openspec/changes/dhammapada-catalog-lookup/` — the authoritative plan.

### 7. Secure the domain and handles

Buy `idleashes.com` before someone else takes it. If parallel to `freelyspoken`, also grab handles on relevant social/app-store platforms.

## Quick FAQ

**Why not just ask Gemini for "a Dhammapada verse that fits"?**
It hallucinates verse numbers and wording — passages that don't exist or chimeras of three translations. The catalog exists so the LLM picks from real, approved options instead of inventing.

**Why human review if we use an LLM for labels?**
Two reasons. The LLM's tone judgment is fine on average but fails specifically on the cases that matter most — vulnerable states. And the labels drive who gets shown what; that's a product decision that needs human ownership, not full delegation.

**How do I know labeling worked?**
Fixture tests. Run your 10–20 fixture inputs through the selector; check if the returned verses make sense. If they don't, the rubric or vocabulary needs revision — not the individual labels.

**Rough timeline sketch?**
- Translation + rights review: a few days of focused research.
- Vocabulary + rubric: a weekend of sit-down work.
- 50-verse subset labeling + review + provider eval: ~a week.
- Adapter implementation + harness iteration: ~a week.
- Fixture testing + revision: open-ended.
- Full 423-verse expansion: only after the small-subset version proves itself in user testing.
