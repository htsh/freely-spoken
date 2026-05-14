# Lookup Harness Plan (2026-05-13)

## Purpose

A small Mac-local web app that exercises the **text half** of the production pipeline — anonymize, sentiment, hosted LLM reference selection — without recording on a phone. The harness lets us iterate on prompts and verse-selection behavior with fast turnaround and concrete sample inputs, and lets us hold the v1 product in our hand before committing to its shape.

This harness is also where v2 (Stoic) will be prototyped later via a variant switch.

## What this is and isn't

**Is:**
- A prototype of the production hosted lookup backend. The contract it commits to between *anonymized text + sentiment metadata* and *reference selection* should be the contract the real backend uses.
- A Mac-local development tool. Runs only where the Swift CLI runs (macOS 26, Apple Silicon, Apple Intelligence enabled).
- Single-developer. No auth, no multi-tenant, no persistence beyond optional run logs.

**Is not:**
- Production code. The frontend is a developer tool, not a shipping UI.
- A replacement for end-to-end device testing of the recording + STT pipeline.
- A chat interface. Single-shot, single-result, like the production app.

## What gets tested vs production

```
   Production (Christian v1, on device)
   ┌─────────┐  ┌────┐  ┌─────────────┐  ┌────────────┐  ┌──────────┐  ┌────┐
   │ record  │─▶│STT │─▶│ Apple FM    │─▶│ hosted LLM │─▶│ Bible    │─▶│ UI │
   │ audio   │  │    │  │ sentiment + │  │ verse pick │  │ API      │  │    │
   └─────────┘  └────┘  │ anonymize   │  └────────────┘  └──────────┘  └────┘
                        └─────────────┘
                              ▲
                              │ same prompt as Swift CLI; same code path
                              │
   Harness (Mac-local web app)
   ┌─────────┐         ┌─────────────┐  ┌────────────┐  ┌────┐
   │ pick    │────────▶│ Swift CLI   │─▶│ hosted LLM │─▶│ UI │
   │ sample  │         │ subprocess  │  │ verse pick │  │    │
   └─────────┘         └─────────────┘  └────────────┘  └────┘
                                                          ▲
                       (audio + STT skipped)              │
                       (Bible API fetch deferred) ────────┘
```

The harness exercises the **lookup half** — the new, uncertain part. The recording/STT half already works on-device and is not where the design risk lives. The Bible API fetch is the next stage after this plan completes; spec for that API will arrive later.

## Confirmed decisions

1. **Prototype, not throwaway.** Backend shape should match the eventual production lookup backend so the LLM contract carries over.
2. **Swift subprocess per request.** Every harness call shells out to the existing `tools/sentiment-cli/` binary. Slower but real, and avoids fixture-staleness when the analyzer prompt changes.
3. **Stop at LLM verse-pick output.** No Bible API fetch in this plan. Result of a harness run is `{ ref, shortReason }` plus the pre-LLM metadata. Verse text fetch is the next stage.
4. **Variant switch in the UI from Stage 2 onward.** Christian works; Stoic is plumbed but stubbed until the Stoic catalog exists.

## Proposed but not yet confirmed

These are recommendations. Push back on any of them before implementation starts.

| Decision | Recommendation | Why | Alternative |
|---|---|---|---|
| Backend stack | FastAPI (Python) | Matches the stated VPS direction in `project_direction.md`. Keeps prototype reusable. | Node/Express, Bun/Hono |
| Frontend | Server-rendered Jinja templates + minimal JS, or HTMX | Single process, no bundler, fastest iteration | React + Vite (overkill for a dev tool) |
| Repo location | `tools/lookup-harness/` | Parallels `tools/sentiment-cli/` | Top-level `harness/`, separate repo |
| Verse reference shape | Plain string `"John 3:16"` | Matches bible-api.com URL form, LLM produces it reliably, human-readable | OSIS IDs (`JHN.3.16`), structured `{book, ch, v}` |
| LLM provider for Stage 2 | Gemini Flash only at first | Memory says primary. Skip fallback machinery until we hit a 429 in real iteration. | Add OpenRouter fallback now |
| Verse selection output | Ranked top-3 with `primary`, `alternates` | 3× signal per call; reveals what the LLM nearly picked; cheap to display | Single verse only |
| Swift CLI invocation | Add `--json` flag to CLI that emits structured JSON only | Harness needs to parse output programmatically; current human-readable format is fragile to parse | Parse current output (fragile), or pipe to a wrapper script |
| Crisis-language handling | Flag-but-don't-handle in Stage 2: log a `crisisFlag: bool` based on simple keyword detection on anonymized text | Pay attention from day one without scope-creeping the harness | Defer entirely |

## Repo layout

```
tools/lookup-harness/
├── README.md
├── pyproject.toml             # or requirements.txt; FastAPI + httpx + jinja2
├── app/
│   ├── main.py                # FastAPI app entry
│   ├── routes.py              # /, /run, /api/select
│   ├── pipeline.py            # subprocess wrapper around sentiment-cli
│   ├── lookup/
│   │   ├── base.py            # appVariant boundary + interface
│   │   ├── christian.py       # Christian verse-pick prompt + Gemini call
│   │   └── stoic.py           # Stoic stub (Stage 2.5 / v2)
│   ├── providers/
│   │   └── gemini.py          # thin Gemini Flash client
│   └── templates/
│       ├── index.html         # sample picker, variant toggle, run button
│       └── result.html        # rendered run output
├── fixtures/
│   └── samples.json           # the 20+ sample inputs (importable from tools/sentiment-cli/run-anonymization-samples.sh)
└── .env.example               # GEMINI_API_KEY=
```

## Stage-gated build

Each stage is a working harness by the end of it. Stop at any stage if friction tells you to.

### Stage 0 — bootstrap

- Create `tools/lookup-harness/` skeleton.
- FastAPI app boots at `localhost:8000`.
- One route: `GET /` renders the picker template (samples list, variant toggle, run button — button is no-op).
- `fixtures/samples.json` is seeded from the 20 inputs in `tools/sentiment-cli/run-anonymization-samples.sh`. Each sample has `{ id, text, notes? }`.

**Done when:** page renders the sample list and you can click around without errors.

### Stage 1 — Swift subprocess + display

- Add `app/pipeline.py` with `run_sentiment(text: str) -> SentimentResult` that:
  - Shells out to `swift run sentiment-cli --json` (or current CLI if `--json` not yet added; flag this as a prerequisite step before Stage 1 completes).
  - Captures stdout, parses JSON.
  - Returns `{ sentiment, emotions, confidence, anonymizedText, rawStrategy, raw }`.
- Add `POST /run` that takes `{ sampleId }`, runs the sample text through `run_sentiment`, renders `result.html` with all fields visible.
- UI shows: original sample, anonymized text, sentiment, emotion list, confidence, raw model output (collapsible), strategy badge (`generateObject` vs `generateText-fallback`).

**Done when:** clicking a sample shows real Swift CLI output in the browser within a few seconds. No LLM yet.

**Prerequisite:** Swift CLI needs a `--json` flag emitting structured JSON only. Add it to `tools/sentiment-cli/Sources/sentiment-cli/main.swift` and document in its README. The TS guard and current `--raw` flag stay as they are.

### Stage 2 — LLM verse selection

- Add `app/lookup/base.py` defining:
  ```
  class LookupRequest:
      anonymized_text: str
      sentiment: str
      emotions: list[str]
      confidence: str
      crisis_flag: bool

  class LookupResult:
      primary: Reference
      alternates: list[Reference]
      provider: str
      model: str
      retry_count: int

  class Reference:
      ref: str             # "John 3:16"
      short_reason: str    # 1–3 sentences

  class LookupAdapter(Protocol):
      app_variant: str
      def select(self, req: LookupRequest) -> LookupResult: ...
  ```
- Add `app/lookup/christian.py`:
  - Holds the Christian verse-pick system prompt (drafted in this stage; iterated in Stage 3).
  - Calls Gemini Flash via `app/providers/gemini.py`.
  - Parses model output into `LookupResult`. Fails clearly if the model deviates from the schema.
- Add `app/lookup/stoic.py` as a stub adapter that returns a `NotImplementedError`-equivalent payload. Wired in so the variant toggle in the UI works end-to-end without picking Stoic in production yet.
- `POST /run` now calls `LookupAdapter.select(req)` after sentiment and renders `{ primary, alternates }` in the result template.
- Crisis flag: simple keyword detector (suicide, self-harm, hurt myself, etc.) runs against anonymized text after sentiment; flagged runs still proceed but the UI shows a banner.

**Done when:** pick a sample, hit run, see anonymized text + sentiment + 3 candidate Bible verses with short reasons within ~5–10 seconds. Variant toggle present; Stoic returns a stub.

### Stage 3 (not part of this plan, named for context)

Bible API fetch + render canonical verse text. Waiting on Bible API spec. Plan to be written separately when ready.

## LLM contract for Stage 2

### Input to provider

System prompt holds the Christian-specific framing (drafted at Stage 2, refined as iteration target). User prompt contains:

```
Anonymized text: <anonymized_text>
Sentiment: <sentiment>
Emotions: <comma-joined emotions>
Confidence: <confidence>
```

Crisis flag is **not** included in the LLM call — handling is UI-side only in this stage, to avoid coupling LLM behavior to a keyword detector that will get rewritten.

### Output schema (JSON, enforced)

```json
{
  "primary": { "ref": "John 14:27", "shortReason": "..." },
  "alternates": [
    { "ref": "Psalm 34:18", "shortReason": "..." },
    { "ref": "Philippians 4:6", "shortReason": "..." }
  ]
}
```

Constraints to bake into the prompt:
- `ref` strings must match `^[1-3]?\s?[A-Za-z]+\s\d+:\d+(-\d+)?$` (book, chapter, verse, optional range).
- `shortReason` is 1–3 sentences, plain modern English, no preaching tone.
- Exactly 1 `primary` and exactly 2 `alternates`.
- No verse text in the output — only references and reasons. The Bible API call (later stage) is the source of canonical text.

### Failure modes

- Model returns malformed JSON → harness shows the raw output verbatim and marks the run as failed. Retry is manual, not automatic, in Stage 2 (provider retry/fallback machinery lives in `app/providers/` for later).
- Model returns a valid-looking `ref` that doesn't exist → caught at Stage 3 (Bible fetch). Out of scope here.

## Variant abstraction

`appVariant` is a first-class concept from Stage 2 onward. The UI has a toggle:

```
   ┌─────────────────────────────────┐
   │  Variant: [ Christian ] [ Stoic ] │  ← Stoic disabled with tooltip
   │                                   │     "catalog not yet seeded"
   │  Sample: [ dropdown ▼ ]           │
   │                                   │
   │  [ Run ]                          │
   └───────────────────────────────────┘
```

Backend resolves `appVariant` to a `LookupAdapter` implementation. `christian.py` is real; `stoic.py` is a stub that returns a clear "not yet implemented" payload so the UI can render something instead of crashing.

When Stoic v2 work starts, the only changes needed are:
- A real `stoic.py` adapter (prompt + Gemini call + parsing).
- A Stoic catalog index file passed into the prompt.
- Per `docs/stoic-curation-rubric.md`, the prompt must enforce the bro-Stoic exclusion rules.
- Enable the Stoic toggle in the UI.

No frontend rework, no contract change.

## Sample fixtures

Source: the 20 samples in `tools/sentiment-cli/run-anonymization-samples.sh`. These exercise the anonymizer hard (names, addresses, accounts, medical, legal). For verse selection, the value is the *emotional content underneath* the privacy noise — fear, shame, anger, helplessness, panic.

Migration: copy the array into `fixtures/samples.json` with stable IDs (`s01`–`s20`). Keep the shell script as the canonical seed; the JSON is a derived artifact regenerated when the shell list changes.

Add a free-form text input next to the picker so non-fixture inputs can be tried ad hoc.

## Out of scope for this plan

- Bible API selection, request shape, translation choice, license check.
- Reading verses aloud.
- Stoic catalog construction and Stoic prompt drafting (separate plan; Stoic adapter stays a stub here).
- Provider fallback (Gemini → OpenRouter) and retry/jitter logic.
- Persistence of runs across restarts.
- Multi-user concerns: auth, rate limiting, abuse detection.
- Deploying the harness anywhere off the developer's Mac.
- Mocking the Swift step for portability — fixture-based mode can come later if needed.

## Open questions

1. **Swift CLI `--json` flag** — must be added before Stage 1 completes. Confirm shape of the JSON before writing the wrapper.
2. **FastAPI vs alternatives** — confirm before Stage 0 starts. Default recommendation is FastAPI; happy to switch to Node if you'd rather stay in one language across the project.
3. **Frontend approach** — templates + HTMX vs minimal React. Default is templates.
4. **Verse output format** — confirm plain `"John 3:16"` strings or commit to a different ID scheme now to avoid migration later.
5. **One-or-three verses from LLM** — recommendation is ranked 1 + 2 alternates for visibility; confirm.
6. **Crisis flag** — keyword detector now, or defer entirely?
7. **Run logging** — should runs be persisted to a local SQLite or JSONL for later review? Useful for catching regressions after prompt edits. Not strictly required for Stage 2.

## Links

- `CLAUDE.md` — project shape, on-device pipeline, debug tools section.
- `tools/sentiment-cli/README.md` — the Swift CLI this harness wraps.
- `tools/sentiment-cli/run-anonymization-samples.sh` — source of the 20 sample inputs.
- `docs/plans/2026-05-11-verse-lookup-brainstorm-notes.md` — earlier brainstorm on hosted lookup.
- `docs/plans/2026-05-13-two-version-product-direction.md` — variant boundary direction.
- `docs/stoic-curation-rubric.md` — governs Stoic adapter content rules when v2 starts.
- `docs/other_sources.md` — v3+ candidate corpus list and provenance rules.
