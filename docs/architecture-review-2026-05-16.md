# Architecture Review: Deepening Opportunities

Date: 2026-05-16
Skill: improve-codebase-architecture

---

## 1. Extract the sentiment pipeline into testable modules

**Files:** `hooks/use-sentiment-analyzer.ts` (~360 lines)

**Problem:** This is the largest and most business-critical module in the app. It contains the prompt, JSON schema, alias maps, 5 normalization functions, 6 privacy-guard functions, topic inference, fallback text generation, a hand-written JSON extractor, *and* the React hook — all in one file. The privacy guard is the core value proposition (only anonymized text leaves the device), yet it's impossible to unit-test without mounting the hook and calling the on-device AI. If you change `SENTIMENT_PROMPT` or the anonymization rules, you have no fast feedback loop — you must run on a real device or the Swift CLI.

**Solution:** Split into 4 seams behind a single `analyze` interface:
- `sentiment/prompt.ts` — `SENTIMENT_PROMPT`, `SENTIMENT_SCHEMA`, `EMOTIONS`, `SENTIMENTS`
- `sentiment/normalize.ts` — `normalizeSentiment`, `normalizeEmotions`, `normalizeConfidence`, `normalizeAnonymizedText`, plus alias maps
- `sentiment/privacy.ts` — `extractProtectedTerms`, `containsProtectedTerm`, `containsSensitivePattern`, `containsSensitiveConcept`, `isTooSimilarToSource`, `buildAnonymizedFallback`, topic patterns
- `sentiment/extract.ts` — `extractFirstJSONObject` (the brace-matching parser)

The hook becomes ~80 lines: check availability, call `generateObject`/`generateText`, pipe through `extractFirstJSONObject` → `parseStructuredSentiment` (which delegates to the normalization/privacy modules).

**Benefits:**
- **Locality:** Privacy bugs concentrate in `privacy.ts`, normalization bugs in `normalize.ts`. Change a guard rule without touching the prompt or the hook.
- **Testability:** Unit-test the JSON extractor against malformed model output. Unit-test `normalizeAnonymizedText` against the 20 privacy-heavy fixtures from `run-anonymization-samples.sh` *without* the Swift CLI or a device. The interface (hook) becomes the test surface for integration; the seams become the test surface for logic.
- **Leverage:** The debug screen (`app/debug.tsx`) can import the same normalization and privacy functions directly, rather than indirectly through the hook. The Swift CLI can reference the same prompt text via a shared file (or generate it from the TypeScript source).

---

## 2. Extract the pipeline state machine

**Files:** `app/index.tsx` (611 lines, 5 `useEffect`s + event handlers)

**Problem:** The `idle → recording → processing → responseLookup → results` state machine is implicit. Transitions happen through 3 chained `useEffect`s that check `appState`, `isTranscribing`, `transcript`, `isAnalyzing`, `sentimentResult`, etc. Understanding the full flow requires reading ~50 lines of `useEffect` logic scattered across the file. Adding a new pipeline step (e.g. a "crisis check" after sentiment) means editing 2–3 `useEffect`s and their dependency arrays. The animation `useEffect` (#5) is mixed in with business-logic `useEffect`s. The `app/index.tsx` file mixes UI rendering, state-machine orchestration, animation, and error display.

**Solution:** Extract a `usePipeline` hook that owns the state machine. It consumes the 4 existing hooks and exposes `{ appState, start, stop, result, error }`. The state machine becomes explicit — a reducer or a small state machine function with clear transitions. `app/index.tsx` shrinks to ~200 lines: UI rendering, event wiring to `usePipeline`, and the animation `useEffect`.

**Benefits:**
- **Locality:** State transitions live in one place. A bug in the "skip lookup on empty transcript" path is found in the state machine, not by tracing `useEffect` #1 → `useEffect` #2.
- **Testability:** The state machine can be tested independently by mocking the 4 pipeline hooks. Feed it mocked `{ transcript, sentimentResult, lookupResult }` sequences and assert `appState` transitions.
- **Deletion test:** Delete `usePipeline` and the orchestration complexity reappears across `app/index.tsx` — it was earning its keep.

---

## 3. Deduplicate the privacy guard between TypeScript and Swift CLI

**Files:** `hooks/use-sentiment-analyzer.ts`, `tools/sentiment-cli/Sources/sentiment-cli/main.swift`

**Problem:** `AGENTS.md` explicitly warns: "The Swift CLI mirrors the anonymized-text guard and prints both raw model output and guarded anonymized text. Keep the CLI and TypeScript guard rules in sync when changing privacy behavior." This is a manual cross-language synchronization hazard. If you tighten a rule in TypeScript but forget the Swift CLI, your macOS debug tool gives false confidence while the device behaves differently.

**Solution:** Define the privacy rules as structured data (JSON/YAML) that both implementations consume. The TypeScript `sentiment/privacy.ts` module (from candidate 1) loads the rule file. The Swift CLI reads the same file at runtime. Rules include: protected term patterns, sensitive regexes, topic mappings, stopword lists, similarity threshold (0.65).

**Benefits:**
- **Locality:** One file = one source of truth for privacy behavior.
- **Leverage:** Change the threshold from 0.65 → 0.70 in one file, both implementations update.
- **Testability:** Run the 20 privacy fixtures through the shared rules once, assert both implementations pass.

---

## Recommended priority

1. **Candidate 1** (sentiment pipeline extraction) — highest leverage. The privacy and normalization logic is the most critical and currently hardest to verify.
2. **Candidate 2** (pipeline state machine) — once the sentiment hook shrinks, the state machine extraction becomes cleaner.
3. **Candidate 3** (privacy guard deduplication) — follow after candidate 1 establishes the `sentiment/privacy.ts` seam.
