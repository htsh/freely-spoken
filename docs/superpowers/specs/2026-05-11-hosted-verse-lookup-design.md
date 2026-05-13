# Hosted Spiritual Response Lookup Design (Short Spec)

Date: 2026-05-11

## 1. Goal

Add a hosted LLM lookup step after on-device anonymization to return one focused spiritual response for a single user submission.

The product direction is now two related versions:

- Christian version: scripture-oriented response. The LLM selects a verse reference; the app fetches the verse text from a Bible API.
- Zen version: Zen-oriented response. The LLM selects a koan/reference; the app fetches the koan text from a koan collection.

## 2. Non-Goals

- No chat interface
- No persistent conversation memory
- No backend service in this phase
- No sending raw transcript or audio to hosted providers
- No broad multi-tradition product in this phase beyond the Christian and Zen versions

## 3. User Flow

`idle -> recording -> processing (transcription + anonymization) -> responseLookup -> results`

The hosted lookup step consumes only:

- `anonymizedText`
- optional normalized emotional context (`sentiment`, `emotions`, `confidence`)
- fixed app/version context for either `christian` or `zen`

## 4. Functional Requirements

1. App sends anonymized text to hosted provider and requests one relevant canonical reference for the active version.
2. App validates the LLM selection into strict shape:
   - `reference: string`
   - `shortReason: string`
3. App fetches canonical source text for the selected reference:
   - Christian: Bible API
   - Zen: koan collection
4. App renders fetched source text, not provider-generated canonical text.
5. App may optionally read the fetched verse or koan aloud.
6. If primary provider returns `429`, app attempts fallback provider.
7. App performs bounded retry for transient errors (`429`, `5xx`, timeout) with jitter.
8. App returns strategy metadata for debug/UI diagnostics:
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

Create a dedicated hook, still likely named around the first implementation such as `hooks/use-verse-lookup.ts`, or renamed before implementation to a more neutral boundary such as `hooks/use-spiritual-response-lookup.ts`, returning:

- `result`
- `isLoading`
- `error`
- `lookup(input)`
- `reset()`

Internals should use a provider adapter interface:

`lookupSpiritualResponse(input, providerConfig) -> SpiritualResponseResult`

This keeps provider-specific APIs isolated from UI/state machine logic.

The provider adapter should be split conceptually into two steps:

1. `selectReference(input, providerConfig) -> ReferenceSelection`
2. `fetchCanonicalText(selection, appVariant) -> CanonicalTextResult`

This keeps LLM relevance matching separate from trusted content retrieval.

## 7. Privacy and Safety Requirements

1. Never send raw transcript or recording URI off-device.
2. Never include direct identifiers in hosted prompt payload.
3. On schema mismatch, do not display unvalidated free-form provider output.
4. Log only safe debug metadata (attempt count/provider/error class), not raw user text.
5. Do not display provider-generated Bible verse text or koan text as canonical source text.

## 8. Extensibility

Prepare for the two-version direction by adding a single enum field in lookup input:

- `appVariant: "christian" | "zen"`

Do not add broader tradition values until the product direction explicitly expands. The current scope is Christian and Zen only.

## 9. Acceptance Criteria (Phase 1)

1. Successful path returns one Christian verse reference, fetches verse text from the Bible API, and renders fetched text in results view.
2. Forced `429` on primary triggers fallback and still returns a valid response when fallback succeeds.
3. Transient failure path retries within bounds and surfaces clear failure when exhausted.
4. Network payload inspection confirms only anonymized text is transmitted.
5. If read-aloud is included in the phase, playback uses the fetched canonical text.

## 10. Deferred Follow-Up Spec

Before implementing the Zen version, write a separate short spec that defines:

- Zen response shape
- Source/corpus strategy
- Koan identifier and lookup strategy
- Evaluation of candidate sources: Terebess Asia Online, Internet Sacred Text Archive, Wikisource, and licensed GitHub datasets
- License/provenance constraints for displaying or redistributing koan text
- Read-aloud behavior
- Tone and safety constraints
- Whether the UI is a separate app target, separate build configuration, or a development-time variant switch
