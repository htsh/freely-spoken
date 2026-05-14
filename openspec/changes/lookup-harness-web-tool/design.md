## Context

The production iOS app (`mic-check`) records audio, transcribes it with Apple Speech, anonymizes + extracts sentiment with Apple Foundation Models on-device, then needs a hosted LLM step to select a relevant Bible verse. The full device cycle (record → STT → sentiment → lookup) takes 5+ minutes per iteration, and prompt tuning is painful. This harness isolates the _lookup half_ of the pipeline so developers can iterate on verse-selection prompts with sample inputs in under 10 seconds.

The harness is also the proving ground for a future Stoic variant (v2) of the product. The variant abstraction must be real from Stage 2 onward so that adding Stoic later is a pure backend change.

## Goals / Non-Goals

**Goals:**

- Provide a Mac-local web UI that runs sample text through the Swift sentiment CLI and displays results.
- Connect the sentiment output to Gemini Flash for Christian verse selection, returning a ranked top-3 set of references with short reasons.
- Establish the exact JSON contract between _anonymized text + sentiment metadata_ and _verse references_ — this contract will be the contract the production backend uses.
- Wire a Christian/Stoic variant toggle end-to-end, with Stoic returning a clear stub payload.
- Flag crisis-adjacent language in the UI without halting the pipeline.

**Non-Goals:**

- No Bible API fetch (verse text retrieval is Stage 3, out of scope).
- No audio recording, STT, or device testing — this is a text-only harness.
- No chat interface or multi-turn conversation — single-shot, single-result, matching the production app.
- No provider fallback (Gemini → OpenRouter) — Gemini Flash free tier only for now.
- No auth, rate limiting, multi-tenant, or deployment off the developer's Mac.
- No persistence of runs across restarts — purely ephemeral.
- No replacing the Swift CLI with a fixture/mock mode — subprocess per request, slower but real.

## Decisions

| Decision              | Choice                                                    | Rationale                                                                                                                                                                                                                            |
| --------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Backend framework     | FastAPI (Python)                                          | Matches the stated VPS direction in `project_direction.md`. Single process, async-friendly for the Swift subprocess + Gemini I/O overlap. Alternative: Node/Express — rejected to keep Python skills aligned with eventual backend.  |
| Frontend              | Jinja2 templates + minimal vanilla JS                     | No bundler, no build step. Fastest iteration for a developer tool. A React + Vite stack would add complexity with no UX payoff for this audience.                                                                                    |
| Swift CLI invocation  | Subprocess per request (`swift run sentiment-cli --json`) | Slower (~3-5s) but guarantees the harness is always using the current CLI code and prompts. Rejected: pre-building a binary (stale fixtures) or a long-lived Swift daemon (complexity).                                              |
| LLM provider          | Gemini Flash (free tier) only                             | Primary per project direction. Fallback machinery deferred until we actually hit a 429 in real iteration.                                                                                                                            |
| Verse reference shape | Plain string `"John 3:16"`                                | Matches `bible-api.com` URL form, LLM produces it reliably, human-readable. Rejected: OSIS IDs (`JHN.3.16`) — less readable for a dev tool.                                                                                          |
| Verse output          | Ranked top-3: `primary` + 2 `alternates`                  | 3× signal per call reveals what the LLM nearly picked; cheap to display. Rejected: single verse only — hides model uncertainty.                                                                                                      |
| Crisis handling       | Flag in UI, don't gate pipeline                           | We want visibility into crisis-adjacent sample inputs without building crisis-response logic into a dev tool. The LLM call excludes the crisis flag to avoid coupling model behavior to a naive keyword list that will be rewritten. |
| Stoic variant         | Real toggle + stub adapter                                | The variant abstraction must be exercised now so that Stoic v2 is a backend-only change.                                                                                                                                             |

## Risks / Trade-offs

- **[Risk]** Subprocess-per-request latency (~3-5s for Swift CLI + ~2-5s for Gemini) means a full run is ~5-10s. Slow for rapid-fire prompt iteration.
  → **Mitigation**: Acceptable for a dev tool. If it becomes painful, Stage 3 can add a pre-built Swift binary mode.
- **[Risk]** Gemini Flash free tier has rate limits. Heavy iteration could hit 429s.
  → **Mitigation**: Defer fallback to OpenRouter. If hit, add a simple retry-with-backoff in `app/providers/gemini.py`.
- **[Risk]** LLM returns malformed JSON or invalid verse references.
  → **Mitigation**: Parse defensively — show raw output and mark the run as failed. No auto-retry in Stage 2. Invalid refs caught at Stage 3 (Bible API fetch).
- **[Risk]** The Swift CLI `--json` flag adds surface area to a production-adjacent tool.
  → **Mitigation**: The flag is additive only; existing `--raw` and default output are untouched. The TS hook doesn't use the new flag.

## Open Questions

- None outstanding. All decisions from the plan (`docs/plans/2026-05-13-lookup-harness-plan.md`) were confirmed before this design was drafted.
