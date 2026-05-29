<!-- STATUS (2026-05-29): Sections 1, 2 (except 2.8/2.9), and 3 complete.
     Full corpus labeled with deepseek-v4-pro (414/414 rows, 423/423 verses,
     0 failures), backed up at tools/dhammapada-labeling/labeled/. Provider
     decision + rationale in provider-eval-results.md.
     NEXT: 2.8 human review of high-risk labels (trim over-broad avoidWhen,
     set excludeOnCrisis, populate reviewedBy) → then Section 4 backend
     adapter planning. Promotion to server/app/lookup/dhammapada_catalog.json
     is task 5.2, gated on 2.8. -->

## 1. Source and rights review (blocking gate — no section 2+ work begins until 1.1-1.3 land)

- [x] 1.1 Confirm the exact Dhammapada translation/edition to use as canonical app content
- [x] 1.2 Verify public-domain or app-compatible licensing status for the chosen source
- [x] 1.3 Record translator, source URL, publication/source notes, public-domain status, and license note required for every catalog entry
- [x] 1.4 Decide whether to seed all 423 verses or start with a curated subset

## 2. Catalog design and curation

- [x] 2.1 Define the catalog schema: `id`, `tradition`, `source`, `chapter`, `chapterNumber`, `verseNumber`, `passageRef`, `displayLabel`, `text`, `translator`, `sourceUrl`, `publicDomainStatus`, `licenseNote`, `themes`, `useWhen`, `avoidWhen`, `tone`, `summary`, `emotionalFit`, `vulnerableStatesToAvoid`, `riskNotes`, `excludeOnCrisis`, `labeledBy`, `labeledAt`, `promptVersion`, `reviewedBy`
- [x] 2.2 Choose storage for the first pass: checked-in JSON catalog loaded at startup unless Mongo editing workflow is explicitly needed
- [x] 2.3 Seed canonical text and provenance metadata for each approved verse
- [x] 2.4 Define and freeze the controlled vocabularies for `themes`, `useWhen`, `avoidWhen`, `tone`, `emotionalFit`, and `vulnerableStatesToAvoid` — enumerate every allowed value in a checked-in vocabulary file before any labeling prompts are drafted. The frozen `tone` and `themes` vocabularies must designate which values are crisis-flag hard-exclusion triggers (see task 4.6)
- [x] 2.4a Define the labeling rubric: what each field means, judgment criteria, examples of correct and incorrect labels, referencing the frozen vocabularies
- [x] 2.4b Define the JSON schema for labeled output: required fields, vocabulary constraints, and per-row provenance fields (`labeledBy`, `labeledAt`, `promptVersion`)
- [x] 2.5 Draft the LLM labeling prompts as two passes: semantic labels (`themes`, `summary`, `emotionalFit`, `useWhen`) and safety/tone labels (`tone`, `avoidWhen`, `vulnerableStatesToAvoid`, `riskNotes`)
- [x] 2.6 Generate first-pass labels for approved passages with the two-pass labeling prompts (deepseek-v4-pro, 414/414 rows, 423/423 verses, 0 failures; backed up at `tools/dhammapada-labeling/labeled/catalog.labeled.deepseek-v4-pro.labeling-v1.0.json`)
- [x] 2.7 Add a catalog validation script/check that catches duplicate IDs, missing required fields, invalid tone values, out-of-vocabulary labels, empty text, and missing provenance
- [ ] 2.8 Review high-risk labels specifically for shame, grief, panic, despair, self-blame, abuse/betrayal, and crisis-adjacent cases; reviewers SHALL populate `reviewedBy` and set `excludeOnCrisis = true` for any passage that bypasses the categorical filters but is still inappropriate when `crisisFlag = true`
- [ ] 2.9 Update the rubric and regenerate labels when fixture testing reveals systematic matching problems

## 3. Labeling tooling and provider selection

- [x] 3.1 Create a development-only Python labeling tool plan under `tools/dhammapada-labeling/` for batch label generation, validation, per-row provenance (`labeledBy`, `labeledAt`, `promptVersion` written into each catalog record, not just into a batch-level log), and review outputs
- [x] 3.2 Define provider/model config inputs for the labeling tool, including provider, model, prompt version, sample limit, retry policy, and output path
- [x] 3.3 Select 20-30 representative Dhammapada passages for provider/model evaluation before labeling the full corpus
- [x] 3.4 Evaluate candidate models on Hugging Face, Fireworks, and Replicate using existing credits where possible
- [x] 3.5 Compare candidates on total estimated cost for 423 verses × 2 labeling passes, JSON validity, schema/vocabulary compliance, label usefulness, safety/tone judgment, latency, and retry behavior
- [x] 3.6 Choose one labeling provider/model for the full catalog run and record the rationale in the change design or follow-up notes (`provider-eval-results.md`: deepseek-v4-pro)
- [x] 3.7 Confirm the offline labeling provider/model is allowed to differ from the runtime lookup provider/model

## 4. Backend adapter planning

- [ ] 4.1 Draft the Dhammapada selector system prompt requiring ID-only selection from the approved catalog index
- [ ] 4.2 Define the compact catalog index shape passed to the LLM, excluding full canonical text
- [ ] 4.3 Define malformed-output handling: invalid JSON, missing fields, nonexistent IDs, duplicate IDs, too many/few alternates, and quoted passage text in `shortReason`
- [ ] 4.4 Implement deterministic shortlist + LLM rerank as the default selection path; treat full-index selection as a fallback triggered only when shortlist measurements show systematic misses
- [ ] 4.4a Define the shortlist heuristic: match `useWhen` and `themes` against sentiment/emotions/anonymized keywords; exclude `avoidWhen` conflicts; produce top 30-60 candidate records
- [ ] 4.4b Add metrics or fixture checks to detect when shortlist misses the best passage and full-index would have caught it (justification gate for the fallback path)
- [ ] 4.5 Define how Dhammapada references map onto the existing `Reference` response fields
- [ ] 4.6 Define the crisis-flag hard-exclusion list: when `crisisFlag = true`, the catalog/shortlist SHALL exclude every passage where `tone` is a harsh tone designated in the frozen vocabulary (e.g. `stern`), any `avoidWhen` value matches a crisis-adjacent state (`acute shame`, `panic`, `despair`, `self-blame`, `abuse disclosure`, `fresh grief`, `suicidal ideation`), `themes` contains a designated high-risk category (death, ascetic-discipline, moral-rebuke), or `excludeOnCrisis == true`
- [ ] 4.7 Confirm exclusion happens in the adapter, before the LLM index is constructed — the LLM SHALL NOT be told a crisis is in progress; it simply sees a smaller, safer index
- [ ] 4.8 Define behavior when crisis-flag exclusion leaves fewer than three eligible passages: the adapter SHALL return a `lookup_unavailable` response rather than relax the filter or substitute LLM-generated content
- [ ] 4.9 Require human review of the full crisis-flag hard-exclusion list (including the set of high-risk tones and themes from the frozen vocabulary) before any release

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
- [ ] 7.6 Verify crisis-flag behavior does not branch the Dhammapada LLM prompt (the LLM is not told a crisis is in progress); the only crisis-driven behavior change SHALL be the catalog/shortlist exclusion enforced in the adapter
- [ ] 7.7 Add tests that with `crisisFlag = true`, passages with a hard-exclusion tone, matching crisis-adjacent `avoidWhen`, in a designated high-risk theme, or with `excludeOnCrisis == true` never appear in primary or alternates regardless of LLM output
- [ ] 7.8 Add a test that when crisis-flag exclusion leaves fewer than three eligible passages, the adapter returns `lookup_unavailable` rather than a degraded result

## 8. Deferred infrastructure decisions

- [ ] 8.1 Re-evaluate whether deterministic shortlist is needed after full-index prompt testing
- [ ] 8.2 Re-evaluate Mongo only if catalog editing/review needs runtime storage
- [ ] 8.3 Re-evaluate Qdrant/vector search only after corpus expansion or measured selection failures
