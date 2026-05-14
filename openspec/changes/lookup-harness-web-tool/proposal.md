## Why

The production iOS app's hosted LLM verse-selection pipeline (anonymize → sentiment → LLM reference pick → Bible API) has no fast iteration path. Testing requires recording audio on-device, waiting for STT, and running Apple Foundation Models on a physical iPhone. Prompt and model changes need 5+ minute cycles. We need a Mac-local web harness that exercises the _text half_ of the pipeline — anonymized text + sentiment metadata → LLM verse selection — with sample inputs and sub-10-second turnaround.

## What Changes

- Add `--json` flag to the existing `tools/sentiment-cli/` Swift executable so it emits structured JSON (not human-readable prose). The TypeScript hook and `--raw` flag stay unchanged.
- Create `tools/lookup-harness/`: a FastAPI web app with Jinja2 templates, running locally on macOS where Apple Intelligence + the Swift CLI are available.
- Seed `fixtures/samples.json` from the 20 privacy-heavy inputs in `tools/sentiment-cli/run-anonymization-samples.sh`.
- Build a pipeline module that shells out to `swift run sentiment-cli --json` per request, parses stdout into a typed `SentimentResult`.
- Integrate Gemini Flash (free tier) for Christian verse selection: take anonymized text + sentiment metadata, return a ranked top-3 set of Bible references with short reasons.
- Add a `crisisFlag` boolean based on keyword detection (suicide, self-harm, etc.) on the anonymized text. Flagged runs show a UI banner but proceed normally.
- Wire a Christian/Stoic variant toggle in the UI. Christian adapter is real; Stoic adapter returns a stub payload so the toggle works end-to-end.
- Result template displays: original sample, anonymized text, sentiment, emotions, confidence, raw model output (collapsible), strategy badge, crisis banner, and the LLM-selected verse references.

## Capabilities

### New Capabilities

- `swift-cli-json-output`: Add `--json` flag to `tools/sentiment-cli/` for machine-readable structured output.
- `harness-core`: FastAPI app, Jinja2 templates, sample picker, variant toggle, run orchestration.
- `verse-lookup`: Gemini Flash integration for Christian Bible verse selection from sentiment metadata. Defines the LLM contract (input prompt shape, output JSON schema with primary + 2 alternates).
- `crisis-detection`: Lightweight keyword-based crisis language detector on anonymized text.
- `variant-system`: Adapter pattern boundary for Christian/Stoic lookup implementations.

### Modified Capabilities

- _(none — this is a net-new developer tool, not a change to existing production capabilities)_

## Impact

- **New directory**: `tools/lookup-harness/` with its own Python dependencies (FastAPI, Jinja2, httpx).
- **Modified directory**: `tools/sentiment-cli/` — adds `--json` CLI flag. No changes to existing `--raw` behavior or the TS hook.
- **No impact on production iOS app** (`app/`, `hooks/`, `ios/`). This is a dev-side tool only.
- **macOS 26 + Apple Silicon + Apple Intelligence required** to run the harness, same as the Swift CLI.
