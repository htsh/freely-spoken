# Hosted Verse Lookup Design (Short Spec)

Date: 2026-05-11

## 1. Goal

Add a hosted LLM lookup step after on-device anonymization to return one relevant Bible verse for a single user submission.

## 2. Non-Goals

- No chat interface
- No persistent conversation memory
- No backend service in this phase
- No sending raw transcript or audio to hosted providers

## 3. User Flow

`idle -> recording -> processing (transcription + anonymization) -> verseLookup -> results`

The verse lookup step consumes only:

- `anonymizedText`
- optional normalized emotional context (`sentiment`, `emotions`, `confidence`)
- fixed `tradition = christian` (phase 1)

## 4. Functional Requirements

1. App sends anonymized text to hosted provider and requests one relevant verse.
2. App validates result into strict shape:
   - `reference: string`
   - `verseText: string`
   - `shortReason: string`
3. If primary provider returns `429`, app attempts fallback provider.
4. App performs bounded retry for transient errors (`429`, `5xx`, timeout) with jitter.
5. App returns strategy metadata for debug/UI diagnostics:
   - `provider`, `model`, `attemptCount`, `fallbackUsed`, `latencyMs`

## 5. Provider Strategy

- Primary: Gemini Flash (free tier)
- Fallback: OpenRouter free model(s)
- Retry policy:
  - Max attempts per provider: 2
  - Backoff: exponential base with random jitter
  - Global max elapsed time target: 8 seconds

If all attempts fail, show a user-safe error and allow quick retry.

## 6. Proposed Module Boundary

Create a dedicated hook: `hooks/use-verse-lookup.ts` returning:

- `result`
- `isLoading`
- `error`
- `lookup(input)`
- `reset()`

Internals should use a provider adapter interface:

`lookupVerse(input, providerConfig) -> VerseLookupResult`

This keeps provider-specific APIs isolated from UI/state machine logic.

## 7. Privacy and Safety Requirements

1. Never send raw transcript or recording URI off-device.
2. Never include direct identifiers in hosted prompt payload.
3. On schema mismatch, do not display unvalidated free-form provider output.
4. Log only safe debug metadata (attempt count/provider/error class), not raw user text.

## 8. Extensibility

Prepare for additional traditions by adding a single enum field in lookup input:

- `tradition: "christian" | "hindu" | "muslim" | "buddhist"`

Phase 1 behavior keeps `christian` fixed. Later phases may expose this in UI while preserving one-shot interaction.

## 9. Acceptance Criteria (Phase 1)

1. Successful path returns one verse with valid schema and renders in results view.
2. Forced `429` on primary triggers fallback and still returns verse when fallback succeeds.
3. Transient failure path retries within bounds and surfaces clear failure when exhausted.
4. Network payload inspection confirms only anonymized text is transmitted.
