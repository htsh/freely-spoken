## Context

The current architecture already has the right shape for Dhammapada:

1. Device records and transcribes on device.
2. Device anonymizes and extracts sentiment/emotions on device.
3. Device sends only anonymized text and sentiment metadata to `POST /lookup`.
4. Backend dispatches by `appVariant`.
5. Adapter selects canonical references.
6. Backend fetches canonical text from a trusted source before responding.

For Christian lookup, the LLM can often rely on broad Bible-reference knowledge, but the implementation still validates references and fetches canonical text from a Bible API. Dhammapada should be stricter: assume the LLM knows the themes of the Dhammapada reasonably well, but does not reliably know exact verse IDs, chapter numbering, or translation wording.

The Dhammapada corpus is small: 423 verses. That changes the retrieval problem. This is not a "large unstructured knowledge base" problem; it is a "curated catalog selection" problem.

## Goals / Non-Goals

**Goals:**

- Add a future `dhammapada` variant without changing the privacy boundary.
- Store the full approved Dhammapada corpus in a backend-owned catalog.
- Use LLM-assisted labeling to generate first-pass retrieval metadata for each passage: themes, use-when, avoid-when, tone, summary, and risk notes.
- Keep humans responsible for the label rubric, schema, high-risk review, and fixture-based quality checks.
- Let the LLM match an anonymized user situation to known catalog IDs only.
- Validate returned IDs and fetch canonical text from the catalog.
- Keep the first version simple enough for the current VPS class; no separate vector database required.
- Make tone safety first-class so the selector avoids moralizing passages for vulnerable user states.

**Non-Goals:**

- No implementation in this planning change.
- No Qdrant/vector search for the initial Dhammapada adapter.
- No automated scraping pipeline until the exact source/translation/license is approved.
- No LLM-authored Dhammapada text.
- No generic Buddhist advice, dharma teaching, therapy guidance, or multi-turn response.
- No multi-corpus retrieval across Dhammapada, Tao Te Ching, Analects, etc.

## Data Model

Use a stable catalog record for each approved passage:

```json
{
  "id": "dhp-001",
  "tradition": "buddhist",
  "source": "Dhammapada",
  "chapter": "The Twin Verses",
  "chapterNumber": 1,
  "verseNumber": 1,
  "passageRef": "Dhammapada 1",
  "displayLabel": "Dhammapada 1",
  "text": "Canonical approved verse text goes here.",
  "translator": "Translator name",
  "sourceUrl": "https://www.gutenberg.org/files/2017/2017-h/2017-h.htm",
  "publicDomainStatus": "public-domain-us",
  "licenseNote": "Exact edition/license note after rights review.",
  "themes": ["mind", "speech", "consequences"],
  "useWhen": ["rumination", "speech regret", "reactivity"],
  "avoidWhen": ["acute shame", "panic", "self-blame"],
  "tone": "direct",
  "summary": "Actions and words follow the state of the mind.",
  "emotionalFit": ["rumination", "reactivity"],
  "couldThisSoundBlaming": true,
  "vulnerableStatesToAvoid": ["acute shame", "self-blame"],
  "riskNotes": "May sound like blame if the user is already ashamed."
}
```

`text` is canonical app content. `summary`, `themes`, `useWhen`, `avoidWhen`, `tone`, `emotionalFit`, `couldThisSoundBlaming`, `vulnerableStatesToAvoid`, and `riskNotes` are retrieval metadata, not user-facing canonical text.

## Labeling Strategy

The catalog should be labeled with an LLM-assisted workflow, not by hand-tagging all 423 verses from scratch.

```text
approved canonical verse
  │
  ▼
labeling prompt + fixed schema + controlled vocabulary
  │
  ▼
LLM-generated retrieval/tone metadata
  │
  ▼
schema validation and vocabulary validation
  │
  ▼
human review of high-risk and ambiguous entries
  │
  ▼
fixture lookup tests
  │
  ▼
revised rubric / relabeling pass if needed
```

Humans should define the label vocabulary and review the labels that affect safety or product tone. The LLM should do the repetitive first-pass classification.

The labeling prompt should optimize for matching, not academic taxonomy. It should answer:

- What user emotional states is this passage useful for?
- When might this passage be unhelpful, blaming, stern, or invalidating?
- What tone would a vulnerable user likely experience?
- What compact summary helps a selector match this passage without seeing full canonical text?

The matching objective is:

```text
Given:
  anonymized user situation
  sentiment
  emotions

Find:
  a passage whose emotional use-case fits
  whose tone will not hurt
  whose meaning is concrete enough to land
```

Use two labeling passes so semantic usefulness and safety/tone do not get blurred:

```text
Pass 1: semantic labels
- themes
- summary
- emotionalFit
- useWhen

Pass 2: safety/tone labels
- tone
- avoidWhen
- couldThisSoundBlaming
- vulnerableStatesToAvoid
- riskNotes
```

Example label output:

```json
{
  "id": "dhp-005",
  "themes": ["anger", "non-hatred", "reconciliation"],
  "useWhen": ["resentment", "conflict", "reactivity"],
  "avoidWhen": ["fresh grief", "abuse disclosure", "acute shame"],
  "tone": "gentle",
  "summary": "Hatred is not resolved by more hatred; peace comes through non-hatred.",
  "emotionalFit": ["anger", "bitterness", "conflict"],
  "couldThisSoundBlaming": false,
  "vulnerableStatesToAvoid": ["abuse disclosure", "fresh grief"],
  "riskNotes": "Could feel invalidating if the user is describing harm done to them."
}
```

Review priority should be highest for passages whose generated labels mention:

- acute shame
- panic
- grief
- abuse, betrayal, or harm done by another person
- self-blame
- despair
- crisis-adjacent language

The labeling workflow should be repeatable. If fixture testing shows poor matches, update the rubric and regenerate labels rather than one-off editing disconnected fields.

## Labeling Tooling and Provider Selection

Label generation is an offline data-prep job, not part of the runtime lookup path. The likely implementation is a Python batch tool under a development-only location such as:

```text
tools/dhammapada-labeling/
  label_catalog.py
  prompts/
  fixtures/
  outputs/
```

The script should:

1. Load approved canonical Dhammapada records.
2. Run the semantic-label prompt for each selected passage.
3. Run the safety/tone-label prompt for each selected passage.
4. Validate the structured output against the schema and controlled vocabularies.
5. Write a draft labeled catalog.
6. Mark risky rows for human review.
7. Record the provider, model, prompt version, run timestamp, and estimated cost for auditability.

Provider/model choice should happen in this offline labeling phase, before labeling the full corpus. The initial candidate providers are:

- Hugging Face
- Fireworks
- Replicate

Use existing credits on those platforms as the first constraint. Price matters, but the cheapest model is only acceptable if it produces valid JSON, useful matching labels, and reasonable safety/tone judgments.

Recommended selection spike:

```text
20-30 representative verses
  │
  ├─ run semantic + safety/tone prompts on Hugging Face candidate model(s)
  ├─ run semantic + safety/tone prompts on Fireworks candidate model(s)
  └─ run semantic + safety/tone prompts on Replicate candidate model(s)
       │
       ▼
compare:
  - total estimated cost for all 423 verses × 2 passes
  - JSON validity / schema repair rate
  - controlled-vocabulary compliance
  - label usefulness for matching
  - tone and blame-risk judgment
  - latency and retry behavior
       │
       ▼
choose one labeling provider/model for the full run
```

The labeling model does not need to be the same model as the runtime lookup model.

```text
Offline labeling optimizes for:
  careful judgment
  strong structured output
  nuance around tone and blame risk
  low total batch cost using available credits

Runtime lookup optimizes for:
  fast response
  cheap per-request cost
  reliable JSON
  good-enough matching from an approved index
```

So it is acceptable to use a stronger or slower model for the one-time labeling batch while keeping runtime lookup on the existing provider chain.

## Selection Flow

Initial flow:

```text
anonymizedText + sentiment + emotions
  │
  ▼
Dhammapada adapter
  │
  ├─ loads compact catalog index
  │    id, passageRef, themes, useWhen, avoidWhen, tone, summary
  │
  ├─ LLM selects:
  │    {
  │      "primary": {"id": "...", "shortReason": "..."},
  │      "alternates": [
  │        {"id": "...", "shortReason": "..."},
  │        {"id": "...", "shortReason": "..."}
  │      ]
  │    }
  │
  ├─ backend validates all IDs exist and are unique
  │
  ├─ backend fetches canonical text by ID
  │
  ▼
primary + alternates with canonical text, translator/source metadata, short reasons
```

The prompt should make these rules explicit:

- Choose IDs only from the provided catalog.
- Return exactly one primary and exactly two alternates.
- Do not quote or paraphrase canonical passage text in `shortReason`.
- Use the user's sentiment/emotions to choose a passage tone.
- Avoid `tone: "stern"` or entries with matching `avoidWhen` for shame, grief, panic, despair, and self-blame.
- Prefer concrete, compassionate passages over moralizing passages for vulnerable states.

## Retrieval Strategy

### Default: full compact index

For 423 records, start by passing a compact index to the LLM. The index should exclude full verse text and include only retrieval metadata. This is operationally simple and easy to inspect.

```text
423 compact records
  ≈ small enough for hosted LLM context
  ≈ no separate DB/service needed
  ≈ better than relying on model memory
```

### Fallback: deterministic shortlist

If the full index is too large, slow, expensive, or noisy, add a preselection step before the LLM:

```text
sentiment/emotions + anonymized keywords
  │
  ├─ match themes/useWhen/tone
  ├─ exclude avoidWhen conflicts
  └─ produce top 30-60 candidate records
       │
       ▼
     LLM chooses primary + alternates from shortlist
```

This still does not require vector search. Reviewed LLM-assisted labels should carry more product value than embeddings at this corpus size because tone is the hard part.

### Deferred: vector search

Qdrant or another vector database should be considered only if:

- The catalog expands beyond a few small corpora.
- Reviewed labels cannot recover obvious matches.
- Full-index selection becomes too costly.
- A unified retrieval layer across multiple traditions becomes a real product requirement.

Until then, vector search is extra infrastructure without a clear win.

## Storage Decision

Preferred first pass: checked-in JSON catalog loaded into memory by FastAPI at startup.

Rationale:

- 423 records is tiny.
- No runtime dependency.
- Easy to review in pull requests.
- Easy to validate with tests.
- Works on a small 6-core / 4GB VPS.

Mongo is acceptable if catalog editing/review needs an admin workflow later. Qdrant is not part of the initial plan.

## Response Shape

Reuse the existing `primary + alternates` shape:

```json
{
  "primary": {
    "ref": "Dhammapada 1",
    "shortReason": "1-3 sentences",
    "text": "Canonical passage text",
    "translation": "Translator / translation label"
  },
  "alternates": [
    {
      "ref": "Dhammapada 183",
      "shortReason": "1-3 sentences",
      "text": "Canonical passage text",
      "translation": "Translator / translation label"
    },
    {
      "ref": "Dhammapada 5",
      "shortReason": "1-3 sentences",
      "text": "Canonical passage text",
      "translation": "Translator / translation label"
    }
  ],
  "provider": "gemini",
  "model": "...",
  "retryCount": 0,
  "fallbackUsed": false,
  "crisisFlag": false
}
```

This keeps the device rendering mostly generic. Device copy should branch by variant: Christian says "verse"; Dhammapada says "passage" or "Dhammapada passage."

## Rights / Source Strategy

Candidate source currently noted in docs: Project Gutenberg, `https://www.gutenberg.org/files/2017/2017-h/2017-h.htm`.

Before implementation:

- Verify the exact translation/edition.
- Confirm public-domain or compatible licensing status for display in the app.
- Store translator, source URL, public-domain status, and license note on every catalog record.
- Keep any modern summary/retrieval metadata separate from canonical passage text.

## Risks / Trade-offs

- **[Risk] LLM picks nonexistent or duplicate IDs.** Mitigation: validate every ID against the loaded catalog; reject malformed output and fall through provider retry/fallback behavior.
- **[Risk] Some Dhammapada passages sound harsh when matched poorly.** Mitigation: LLM-generated `tone`, `useWhen`, `avoidWhen`, and `riskNotes` metadata under a fixed rubric, plus human review and prompt rules for shame/grief/panic/despair/self-blame.
- **[Risk] Full index prompt becomes too large or degrades quality.** Mitigation: add deterministic shortlist logic before considering vector search.
- **[Risk] Translation tone affects product feel.** Mitigation: choose source/translation deliberately; run fixture review against common emotional states before shipping.
- **[Risk] LLM-assisted labels may look plausible while encoding bad matching behavior.** Mitigation: validate labels against a controlled vocabulary, review high-risk buckets manually, and add fixture tests that verify known inputs avoid clearly bad-tone passages.
- **[Risk] App Store/release copy may imply Buddhist counseling.** Mitigation: keep UI language to "passage lookup" and avoid therapy/advice claims.

## Open Questions

- Which exact translation/edition should be canonical for v1?
- Should `translation` hold just translator name, or a richer label like `"F. Max Müller translation, public domain"`?
- Should the catalog include chapter-level titles in display copy, or keep references compact (`Dhammapada 5`)?
- How much human review is enough for the first pass: all 423 LLM-labeled verses reviewed, only high-risk labels reviewed, or a curated subset first?
- Should the adapter expose all 423 verses to the LLM initially, or launch with deterministic shortlist from day one?
- Should Dhammapada be the next public variant after Stoic, or should it remain a v3/open-slot candidate until v1 data is available?
