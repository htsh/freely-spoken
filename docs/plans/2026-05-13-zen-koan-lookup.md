# Zen Koan Lookup Plan

## Summary

Build the Zen side as a backend-owned, catalog-grounded lookup flow, not a full RAG system for v1.

The MVP corpus should be **The Gateless Gate / Mumonkan**, not `101 Zen Stories`, because it has stable numbered cases and clearer public-domain signals from sources like Sacred Texts and Wikisource. Sacred Texts lists it as 49 koans and notes the 1934 translation is public domain in the US due to non-renewal; Wikisource also exposes stable case links and copyright status notes.

Chosen defaults:

- Corpus: `The Gateless Gate`, 49 cases.
- Backend: FastAPI on VPS owns full lookup.
- Storage: Mongo stores canonical koan records and metadata.
- Result: koan text plus short reason.
- Read-aloud: deferred until lookup quality is proven.

## Key Design

The Zen flow should mirror the Bible flow structurally:

1. User speaks into the mic.
2. iOS app transcribes on-device and runs sentiment/anonymization on-device.
3. App sends only anonymized text and sentiment metadata to the FastAPI backend.
4. Backend asks the LLM to select one relevant koan ID from a controlled catalog.
5. Backend fetches canonical koan text from Mongo by ID.
6. Backend returns fetched koan text, source metadata, and the LLM's short reason.
7. App renders the koan and reason.

Do **not** let the LLM generate koan text. It should only choose a known ID and explain the match.

## Backend Shape

Create a Zen lookup service with these conceptual pieces:

- `koans` collection in Mongo:
  - `id`: stable ID like `gateless-gate-01`
  - `collection`: `gateless-gate`
  - `caseNumber`: `1`
  - `title`: `Joshu's Dog`
  - `text`: canonical fetched/stored text
  - `sourceUrl`: Sacred Texts or Wikisource URL
  - `translator`: Nyogen Senzaki / Paul Reps where applicable
  - `licenseNote`: short provenance/license note
  - `themes`: curated tags such as `attachment`, `fear`, `ego`, `uncertainty`, `grief`
  - `summary`: short internal retrieval summary, not shown as canonical text

- `POST /api/zen/lookup`:
  - Request: `{ anonymizedText, sentiment, emotions, confidence }`
  - Response: `{ koan: { id, title, collection, caseNumber, text, sourceUrl }, shortReason, metadata }`

- Selection method for v1:
  - Pass the LLM a compact catalog index of all 49 koans: ID, title, themes, summary.
  - Require the LLM to return `{ koanId, shortReason }`.
  - Validate `koanId` exists in Mongo.
  - Fetch and return canonical text from Mongo.

This is "RAG-like" but intentionally lighter than vector RAG. With only 49 koans, embeddings are optional complexity. Add vector search only after expanding beyond Gateless Gate.

## Source Strategy

Use Sacred Texts or Wikisource as the initial canonical source for Gateless Gate.

Do not use Terebess or random GitHub datasets as the first canonical source unless licensing/provenance is reviewed. They remain useful for comparison, alternate translations, and future expansion.

Defer `101 Zen Stories` until a separate rights/provenance pass confirms whether the exact text can be displayed in the app.

## Test Plan

- Unit test backend validation rejects unknown `koanId`.
- Unit test backend never returns LLM-generated koan text.
- Fixture test anonymized inputs like anxiety, grief, anger, uncertainty, and gratitude return valid Gateless Gate IDs.
- Manual test the app flow confirms only anonymized text leaves the device.
- Manual review selected koans for tone: no therapy claims, no over-explaining, no fake Zen advice.

## Assumptions

- VPS backend is acceptable and preferred for hiding LLM keys and centralizing prompt/retry behavior.
- Mongo is acceptable for the small canonical catalog.
- MVP does not include read-aloud.
- MVP does not include embeddings unless the corpus expands.
- Christian and Zen should eventually share the same backend selection/fetch architecture, with separate corpus adapters.
