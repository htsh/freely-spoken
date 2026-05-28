## 1. Source and rights review

- [ ] 1.1 Confirm the exact Dhammapada translation/edition to use as canonical app content
- [ ] 1.2 Verify public-domain or app-compatible licensing status for the chosen source
- [ ] 1.3 Record translator, source URL, publication/source notes, public-domain status, and license note required for every catalog entry
- [ ] 1.4 Decide whether to seed all 423 verses or start with a curated subset

## 2. Catalog design and curation

- [ ] 2.1 Define the catalog schema: `id`, `tradition`, `source`, `chapter`, `chapterNumber`, `verseNumber`, `passageRef`, `displayLabel`, `text`, `translator`, `sourceUrl`, `publicDomainStatus`, `licenseNote`, `themes`, `useWhen`, `avoidWhen`, `tone`, `summary`, `emotionalFit`, `couldThisSoundBlaming`, `vulnerableStatesToAvoid`, `riskNotes`
- [ ] 2.2 Choose storage for the first pass: checked-in JSON catalog loaded at startup unless Mongo editing workflow is explicitly needed
- [ ] 2.3 Seed canonical text and provenance metadata for each approved verse
- [ ] 2.4 Define the labeling rubric, controlled vocabularies, and schema for LLM-generated retrieval and tone-safety metadata
- [ ] 2.5 Draft the LLM labeling prompts as two passes: semantic labels (`themes`, `summary`, `emotionalFit`, `useWhen`) and safety/tone labels (`tone`, `avoidWhen`, `couldThisSoundBlaming`, `vulnerableStatesToAvoid`, `riskNotes`)
- [ ] 2.6 Generate first-pass labels for approved passages with the two-pass labeling prompts
- [ ] 2.7 Add a catalog validation script/check that catches duplicate IDs, missing required fields, invalid tone values, out-of-vocabulary labels, empty text, and missing provenance
- [ ] 2.8 Review high-risk labels specifically for shame, grief, panic, despair, self-blame, abuse/betrayal, and crisis-adjacent cases
- [ ] 2.9 Update the rubric and regenerate labels when fixture testing reveals systematic matching problems

## 3. Labeling tooling and provider selection

- [ ] 3.1 Create a development-only Python labeling tool plan under `tools/dhammapada-labeling/` for batch label generation, validation, and review outputs
- [ ] 3.2 Define provider/model config inputs for the labeling tool, including provider, model, prompt version, sample limit, retry policy, and output path
- [ ] 3.3 Select 20-30 representative Dhammapada passages for provider/model evaluation before labeling the full corpus
- [ ] 3.4 Evaluate candidate models on Hugging Face, Fireworks, and Replicate using existing credits where possible
- [ ] 3.5 Compare candidates on total estimated cost for 423 verses × 2 labeling passes, JSON validity, schema/vocabulary compliance, label usefulness, safety/tone judgment, latency, and retry behavior
- [ ] 3.6 Choose one labeling provider/model for the full catalog run and record the rationale in the change design or follow-up notes
- [ ] 3.7 Confirm the offline labeling provider/model is allowed to differ from the runtime lookup provider/model

## 4. Backend adapter planning

- [ ] 4.1 Draft the Dhammapada selector system prompt requiring ID-only selection from the approved catalog index
- [ ] 4.2 Define the compact catalog index shape passed to the LLM, excluding full canonical text
- [ ] 4.3 Define malformed-output handling: invalid JSON, missing fields, nonexistent IDs, duplicate IDs, too many/few alternates, and quoted passage text in `shortReason`
- [ ] 4.4 Decide whether the first implementation uses full compact-index selection or deterministic shortlist + LLM rerank
- [ ] 4.5 Define how Dhammapada references map onto the existing `Reference` response fields

## 5. Backend implementation tasks

- [ ] 5.1 Add `server/app/lookup/dhammapada.py` adapter implementing the existing lookup adapter protocol
- [ ] 5.2 Add catalog loader and in-memory lookup by ID
- [ ] 5.3 Add ID validation and canonical text enrichment from the catalog
- [ ] 5.4 Register `dhammapada` in the backend variant registry
- [ ] 5.5 Update backend schema/types to accept `appVariant: "dhammapada"`
- [ ] 5.6 Ensure backend logs do not include `anonymizedText` or full passage text

## 6. Device integration tasks

- [ ] 6.1 Update app variant typing/config to allow `dhammapada`
- [ ] 6.2 Add variant-specific UI copy for Dhammapada results, using "passage" rather than "verse"
- [ ] 6.3 Confirm the existing results screen can render `primary + alternates` without Bible-specific labels
- [ ] 6.4 Confirm no raw transcript, audio path, duration, or device identifier is added to the request body

## 7. Quality and safety verification

- [ ] 7.1 Create fixture anonymized inputs for anger, craving, grief, shame, panic, conflict, speech regret, rumination, gratitude, and restlessness
- [ ] 7.2 Run fixture lookups and manually review selected primary/alternate passages for relevance and tone
- [ ] 7.3 Add tests that invalid IDs are rejected and never produce LLM-generated canonical text
- [ ] 7.4 Add tests that duplicate primary/alternate IDs are rejected
- [ ] 7.5 Add tests or fixture assertions for vulnerable states avoiding entries tagged with matching `avoidWhen`
- [ ] 7.6 Verify crisis-flag behavior remains informational and does not branch the Dhammapada prompt

## 8. Deferred infrastructure decisions

- [ ] 8.1 Re-evaluate whether deterministic shortlist is needed after full-index prompt testing
- [ ] 8.2 Re-evaluate Mongo only if catalog editing/review needs runtime storage
- [ ] 8.3 Re-evaluate Qdrant/vector search only after corpus expansion or measured selection failures
