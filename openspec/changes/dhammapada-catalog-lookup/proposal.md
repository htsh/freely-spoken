## Why

The Dhammapada is the strongest current candidate for a future non-Christian wisdom variant because it matches the product's "short, concrete passage" shape: 423 verse-form sayings on anger, craving, grief, speech, mindfulness, reactivity, and conduct. It does not need a heavyweight RAG stack for an MVP. The corpus is small enough to keep as a backend-owned curated catalog and present to an LLM as a controlled selection index.

The important reliability boundary is the same as the Christian lookup flow: the hosted LLM may select and explain, but it must never author canonical sacred/wisdom text. For Dhammapada this matters more than Bible lookup because LLMs are less reliable with exact Dhammapada verse numbers and translation wording than they are with common Bible references.

## What Changes

- Add a future `dhammapada` app variant that uses the existing privacy-first pipeline: the device sends only `{ appVariant, anonymizedText, sentiment, emotions, confidence }`.
- Add a backend-owned Dhammapada catalog with all approved verses and metadata: stable ID, chapter/verse reference, canonical text, translator/source/license metadata, themes, use-when guidance, avoid-when guidance, tone, and internal summary.
- Use LLM-assisted catalog labeling with human review: humans define the label rubric and review high-risk outputs; the LLM generates first-pass structured retrieval and tone-safety metadata.
- Treat labeling as an offline data-prep phase, likely run by a Python script. Choose the labeling provider/model during that phase by comparing Hugging Face, Fireworks, and Replicate against cost, JSON reliability, label usefulness, and tone judgment. Existing credits should be used before adding a new paid provider.
- Add a Dhammapada adapter that gives the LLM a compact approved catalog index and requires it to return exactly one primary passage ID plus two alternate passage IDs with short reasons.
- Validate every returned passage ID against the catalog before fetching canonical text.
- Fetch canonical Dhammapada text from the backend catalog by ID. Never display LLM-generated Dhammapada text.
- Start without Qdrant/vector search. If the full compact index becomes too large or noisy, add deterministic shortlist logic first; consider vector search only after expanding beyond a small curated corpus whose labels have already been reviewed.
- Keep tone safety explicit: avoid stern/moralizing passages for shame, grief, panic, despair, self-blame, or other vulnerable states.

## Capabilities

### New Capabilities

- `dhammapada-lookup-flow`: Backend-owned curated Dhammapada catalog, LLM-assisted labeling with human review, LLM ID selection from approved index, ID validation, canonical text fetch, tone guardrails, and source/license metadata.

### Modified Capabilities

- `variant-routing`: Add `dhammapada` as a supported app variant once the catalog and adapter are ready.
- `lookup-backend-api`: Keep the existing lookup payload and ranked-reference response shape, but allow canonical catalog-backed passages whose `translation` field represents the Dhammapada translation/translator label rather than a Bible translation.

## Impact

- **New backend data**:
  - Curated Dhammapada catalog, initially likely as a checked-in JSON file or equivalent backend-owned seed. Mongo is acceptable if operational editing is needed; Qdrant is intentionally out of scope for the first pass.
- **New backend code**:
  - `server/app/lookup/dhammapada.py` adapter.
  - Catalog loading/validation helper.
- **Modified backend code**:
  - Variant registry and request schema to accept `appVariant: "dhammapada"`.
  - Response handling should remain generic enough to render `primary + alternates`.
- **Modified device code**:
  - Build-time app variant support for `dhammapada`.
  - Variant-specific UI copy so the result is labeled as a Dhammapada passage, not a Bible verse.
- **Docs / policy**:
  - Verify exact translation/source/license before shipping.
  - Update privacy/release docs only when this variant is implemented, not during planning.
- **Out of scope**:
  - Implementing the adapter now.
  - Installing Qdrant or any vector database.
  - Multi-corpus unified retrieval.
  - Chat, memory, accounts, saved history, or generated commentary beyond a short selection reason.
  - Buddhist pastoral advice or therapy-style guidance; the product remains a short passage lookup.
