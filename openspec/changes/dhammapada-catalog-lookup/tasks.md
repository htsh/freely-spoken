<!-- STATUS (2026-05-30): Sections 1, 2, 3, 4 (planning), 5 (backend impl),
     6 (device integration), and 7 (quality/safety tests) complete. All build
     sections done.
     v1.0 labels over-suppressed (97% crisis-excluded). Fixed via labeling
     prompt v1.1 (task 2.9). Re-labeled full corpus with BOTH deepseek-v4-pro
     and kimi-k2p6 under v1.1, then Claude-adjudicated the two verse-by-verse
     into labeled/catalog.labeled.v1.1.adjudicated.json (review/adjudicate.py):
     414/414 valid, 260 eligible under crisis, harsh/death/abuse verses
     correctly excluded. This is the reviewed catalog (task 2.8).
     Section 4 backend adapter planning is captured in adapter-plan.md
     (concrete selector prompt, index shape, malformed handling, shortlist
     heuristic + lexicons, Reference mapping, frozen crisis predicate).
     RECOMMENDED before release (two human gates, do together):
       - task 4.9: sign off the crisis hard-exclusion list as the safety contract.
       - task 2.8 follow-up: confirm the 260 crisis-eligible rows, set
         excludeOnCrisis where any still reads wrong.
     Section 5 done: server/app/lookup/dhammapada.py adapter (shortlist + LLM
     rerank + crisis filter), catalog promoted to dhammapada_catalog.json,
     registered in main.py, schemas widened, LookupRequest.crisis_flag threaded,
     lookup_unavailable payload wired. Verified end-to-end with a stubbed LLM
     (happy path, bad/dup/quoted-id rejection, unavailable floor) + crisis
     predicate asserted equal to vocabulary.json.
     Section 7 done: hermetic pytest suite in server/tests/ (19 tests, green,
     mutation-checked). Task 7.2 live review also done via a Fireworks kimi-k2p6
     stand-in (7.2-live-review-findings.md) — relevance strong; 2 catalog
     tone-flags (grief-under-crisis body verses; speech-regret admonishing tone)
     routed to the human pass; 1 runtime-config note (use constrained JSON decoding).
     Section 6 done: AppVariant += dhammapada, "passage" copy + "Idle Ashes"
     title, lookup_unavailable empty state, buildLookupRequest privacy whitelist
     (vitest). typecheck/lint/vitest all green (36 tests).
     Remaining open gates before release (none block code): task 4.9 (sign off
     crisis exclusion list), task 2.8 follow-up (confirm the 260 crisis-eligible
     rows / set excludeOnCrisis, now informed by the 7.2 flags), and a Gemini
     confirm run of the live review (recommended, not blocking).
     Follow-ups: per-variant native bundle identity (app.config.js for "Idle
     Ashes" name/slug/bundleId); wire server pytest into CI (currently device-only). -->

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
- [x] 2.8 Review high-risk labels specifically for shame, grief, panic, despair, self-blame, abuse/betrayal, and crisis-adjacent cases; reviewers SHALL populate `reviewedBy` and set `excludeOnCrisis = true` for any passage that bypasses the categorical filters but is still inappropriate when `crisisFlag = true` (Claude-adjudicated both v1.1 model outputs verse-by-verse → `labeled/catalog.labeled.v1.1.adjudicated.json` via `review/adjudicate.py`; `reviewedBy` stamped; 260/414 eligible under crisis. **Human confirmation pass on the crisis-eligible set recommended before release.** `excludeOnCrisis` left False — categorical filters cover the harmful set; this is the lever for the human pass.)
- [x] 2.9 Update the rubric and regenerate labels when fixture testing reveals systematic matching problems (v1.0→v1.1 prompt fix for avoidWhen over-suppression; see `provider-eval-results.md` / `provider-eval-results` notes)

## 3. Labeling tooling and provider selection

- [x] 3.1 Create a development-only Python labeling tool plan under `tools/dhammapada-labeling/` for batch label generation, validation, per-row provenance (`labeledBy`, `labeledAt`, `promptVersion` written into each catalog record, not just into a batch-level log), and review outputs
- [x] 3.2 Define provider/model config inputs for the labeling tool, including provider, model, prompt version, sample limit, retry policy, and output path
- [x] 3.3 Select 20-30 representative Dhammapada passages for provider/model evaluation before labeling the full corpus
- [x] 3.4 Evaluate candidate models on Hugging Face, Fireworks, and Replicate using existing credits where possible
- [x] 3.5 Compare candidates on total estimated cost for 423 verses × 2 labeling passes, JSON validity, schema/vocabulary compliance, label usefulness, safety/tone judgment, latency, and retry behavior
- [x] 3.6 Choose one labeling provider/model for the full catalog run and record the rationale in the change design or follow-up notes (`provider-eval-results.md`: deepseek-v4-pro)
- [x] 3.7 Confirm the offline labeling provider/model is allowed to differ from the runtime lookup provider/model

## 4. Backend adapter planning

All concrete artifacts live in `adapter-plan.md` (this change folder).

- [x] 4.1 Draft the Dhammapada selector system prompt requiring ID-only selection from the approved catalog index (adapter-plan.md §4.1)
- [x] 4.2 Define the compact catalog index shape passed to the LLM, excluding full canonical text (adapter-plan.md §4.2 — id/themes/useWhen/tone/summary; avoidWhen deliberately withheld so the LLM cannot reason about crisis state)
- [x] 4.3 Define malformed-output handling: invalid JSON, missing fields, nonexistent IDs, duplicate IDs, too many/few alternates, and quoted passage text in `shortReason` (adapter-plan.md §4.3 — `DhammapadaAdapterError`; structural quotation heuristic, no liturgical phrase list)
- [x] 4.4 Implement deterministic shortlist + LLM rerank as the default selection path; treat full-index selection as a fallback triggered only when shortlist measurements show systematic misses (adapter-plan.md §4.4 — full-index fallback deferred to task 8.1, gated on 4.4b)
- [x] 4.4a Define the shortlist heuristic: match `useWhen` and `themes` against sentiment/emotions/anonymized keywords; exclude `avoidWhen` conflicts; produce top 30-60 candidate records (adapter-plan.md §4.4a — additive score, checked-in USEWHEN/THEME/vulnerable lexicons, default top 45)
- [x] 4.4b Add metrics or fixture checks to detect when shortlist misses the best passage and full-index would have caught it (justification gate for the fallback path) (adapter-plan.md §4.4b — fixture-based shortlist-vs-full miss-rate, ≥10% threshold to build the fallback)
- [x] 4.5 Define how Dhammapada references map onto the existing `Reference` response fields (adapter-plan.md §4.5 — `displayLabel`→`ref`, local `text`, constant Müller `translation`, `textError` always None)
- [x] 4.6 Define the crisis-flag hard-exclusion list: when `crisisFlag = true`, the catalog/shortlist SHALL exclude every passage where `tone` is a harsh tone designated in the frozen vocabulary (e.g. `stern`), any `avoidWhen` value matches a crisis-adjacent state (`acute shame`, `panic`, `despair`, `self-blame`, `abuse disclosure`, `fresh grief`, `suicidal ideation`), `themes` contains a designated high-risk category (death, ascetic-discipline, moral-rebuke), or `excludeOnCrisis == true` (adapter-plan.md §4.6 — predicate reads from `vocabulary.json crisisHardExclusion`; 260/414 eligible)
- [x] 4.7 Confirm exclusion happens in the adapter, before the LLM index is constructed — the LLM SHALL NOT be told a crisis is in progress; it simply sees a smaller, safer index (adapter-plan.md §4.7 — prompt has no crisis language; excluded ids never enter the index)
- [x] 4.8 Define behavior when crisis-flag exclusion leaves fewer than three eligible passages: the adapter SHALL return a `lookup_unavailable` response rather than relax the filter or substitute LLM-generated content (adapter-plan.md §4.8 — checked before shortlisting; `LookupUnavailableError` → structured payload; device gate in 6.2)
- [ ] 4.9 Require human review of the full crisis-flag hard-exclusion list (including the set of high-risk tones and themes from the frozen vocabulary) before any release — **OPEN human gate**, do together with the task 2.8 crisis-eligible confirmation pass (adapter-plan.md §4.9)

## 5. Backend implementation tasks

- [x] 5.1 Add `server/app/lookup/dhammapada.py` adapter implementing the existing lookup adapter protocol (`DhammapadaAdapter.select`; shortlist + LLM rerank + crisis filter)
- [x] 5.2 Add catalog loader and in-memory lookup by ID (`_load_catalog`, module-cached `_CATALOG`/`_CATALOG_BY_ID`; adjudicated catalog promoted to `server/app/lookup/dhammapada_catalog.json`, 414 rows / 260 crisis-eligible)
- [x] 5.3 Add ID validation and canonical text enrichment from the catalog (`_validate_entry` rejects nonexistent/excluded/duplicate ids + quoted text; `_to_reference` enriches from local catalog, `displayLabel`→`ref`)
- [x] 5.4 Register `dhammapada` in the backend variant registry (`main.py` `ADAPTERS`)
- [x] 5.5 Update backend schema/types to accept `appVariant: "dhammapada"` (`schemas.LookupRequestBody`, `base.LookupRequest.crisis_flag`; `LookupUnavailableResult` payload added)
- [x] 5.6 Ensure backend logs do not include `anonymizedText` or full passage text (adapter logs nothing itself; `_log_request` still logs only `anonymized_text_len`; new `lookup_unavailable` log carries no text)

## 6. Device integration tasks

- [x] 6.1 Update app variant typing/config to allow `dhammapada` (`AppVariant` += `'dhammapada'` in `services/lookup-request.ts`; `getBuildAppVariant()` resolves it; build-time config already env-driven via `EXPO_PUBLIC_APP_VARIANT`). NOTE: per-variant native bundle identity (app.json `name`/`slug`/bundleId → "Idle Ashes"/`idleashes`) still needs app.config.js — flagged as a release-packaging follow-up, not runtime.
- [x] 6.2 Add variant-specific UI copy for Dhammapada results, using "passage" rather than "verse" (PRIMARY_HEADINGS / LOOKUP_CTA_LABELS / RESPONSE_NOUN_LABELS dhammapada entries; in-app title via `getBrandName` → "Idle Ashes"; new `lookup_unavailable` gentle empty state rendered)
- [x] 6.3 Confirm the existing results screen can render `primary + alternates` without Bible-specific labels (`ReferenceBlock` is generic — renders `ref`/`text`/`translation`/`shortReason`; dhammapada always carries local text so the fetch-error copy never shows; headings now say "passage")
- [x] 6.4 Confirm no raw transcript, audio path, duration, or device identifier is added to the request body (`buildLookupRequest` whitelists the 5 fields explicitly; vitest `services/__tests__/lookup-request.test.ts` asserts extras are dropped)

## 7. Quality and safety verification

Hermetic pytest suite under `server/tests/` (stubs `dhammapada.run_llm`, no
network). 19 tests, all green; mutation-checked (disabling `_excluded` fails the
crisis tests). Run: `cd server && pip install -e '.[dev]' && pytest`.

- [x] 7.1 Create fixture anonymized inputs for anger, craving, grief, shame, panic, conflict, speech regret, rumination, gratitude, and restlessness (`tests/fixtures/lookup_inputs.json`, 10 inputs incl. expected-axis hints)
- [x] 7.2 Run fixture lookups and manually review selected primary/alternate passages for relevance and tone — ran the real adapter over all 10 fixtures (+ grief/shame/panic under crisis) via Fireworks `kimi-k2p6` stand-in (`tools/dhammapada-labeling/review/live_lookup_review.py`); relevance strong, tone mostly gentle. Findings + 2 catalog tone-flags + 1 runtime-config note in `7.2-live-review-findings.md`. Gemini confirm run recommended before release (not blocking).
- [x] 7.3 Add tests that invalid IDs are rejected and never produce LLM-generated canonical text (`test_nonexistent_id_rejected`, `test_quoted_passage_text_rejected`, `test_unparseable_output_rejected`)
- [x] 7.4 Add tests that duplicate primary/alternate IDs are rejected (`test_duplicate_ids_rejected`)
- [x] 7.5 Add tests or fixture assertions for vulnerable states avoiding entries tagged with matching `avoidWhen` (`test_avoidwhen_penalizes_matching_vulnerable_state` + the crisis-exclusion tests for the hard guarantee)
- [x] 7.6 Verify crisis-flag behavior does not branch the Dhammapada LLM prompt (the LLM is not told a crisis is in progress); the only crisis-driven behavior change SHALL be the catalog/shortlist exclusion enforced in the adapter (`test_prompt_does_not_branch_on_crisis` — identical system prompt, no crisis words, only the index shrinks)
- [x] 7.7 Add tests that with `crisisFlag = true`, passages with a hard-exclusion tone, matching crisis-adjacent `avoidWhen`, in a designated high-risk theme, or with `excludeOnCrisis == true` never appear in primary or alternates regardless of LLM output (`test_crisis_index_excludes_high_risk_passages`, `test_llm_cannot_force_an_excluded_passage`)
- [x] 7.8 Add a test that when crisis-flag exclusion leaves fewer than three eligible passages, the adapter returns `lookup_unavailable` rather than a degraded result (`test_too_few_eligible_returns_lookup_unavailable` — also asserts the LLM is never called)

## 8. Deferred infrastructure decisions

- [ ] 8.1 Re-evaluate whether deterministic shortlist is needed after full-index prompt testing
- [ ] 8.2 Re-evaluate Mongo only if catalog editing/review needs runtime storage
- [ ] 8.3 Re-evaluate Qdrant/vector search only after corpus expansion or measured selection failures
