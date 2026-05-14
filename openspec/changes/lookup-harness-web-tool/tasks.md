## 1. Swift CLI --json Flag (Prerequisite)

- [x] 1.1 Add `--json` flag argument to `tools/sentiment-cli/Sources/sentiment-cli/main.swift`
- [x] 1.2 Implement JSON output formatter emitting `{sentiment, emotions, confidence, anonymizedText, rawStrategy, raw}`
- [x] 1.3 Ensure `--json` output is valid JSON with no surrounding prose; `--raw` and default output remain unchanged
- [x] 1.4 Document `--json` flag in `tools/sentiment-cli/README.md`

## 2. Harness Bootstrap — Stage 0

- [x] 2.1 Create `tools/lookup-harness/` directory with subdirs `app/`, `app/lookup/`, `app/providers/`, `app/templates/`, `fixtures/`
- [x] 2.2 Create `pyproject.toml` with dependencies: FastAPI, Jinja2, httpx, python-dotenv, uvicorn
- [x] 2.3 Create `app/main.py` — FastAPI entrypoint, `GET /` renders `templates/index.html`
- [x] 2.4 Seed `fixtures/samples.json` from the 20 inputs in `tools/sentiment-cli/run-anonymization-samples.sh`, with IDs `s01`–`s20`
- [x] 2.5 Create `templates/index.html` — sample dropdown, Christian/Stoic variant toggle, free-form text input, run button
- [x] 2.6 Add `.env.example` with `GEMINI_API_KEY=` placeholder
- [x] 2.7 Verify: `python -m uvicorn app.main:app --reload` boots on `localhost:8000` and `/` renders without errors

## 3. Swift Subprocess Pipeline — Stage 1

- [x] 3.1 Create `app/pipeline.py` with `run_sentiment(text: str) -> SentimentResult` dataclass
- [x] 3.2 Implement subprocess call to `swift run sentiment-cli --json` with the input text
- [x] 3.3 Parse stdout JSON into `SentimentResult` (sentiment, emotions, confidence, anonymizedText, rawStrategy, raw)
- [x] 3.4 Handle subprocess errors gracefully (non-zero exit, invalid JSON, timeout)
- [x] 3.5 Create `templates/result.html` — displays original text, anonymized text, sentiment, emotions, confidence, strategy badge, raw output (collapsible)
- [x] 3.6 Implement `POST /run` — accepts `{sampleId?}`, looks up sample or uses ad-hoc text, calls `run_sentiment()`, renders `result.html`
- [x] 3.7 Wire free-form text input to bypass sample lookup and pass raw text directly to pipeline
- [x] 3.8 Verify: selecting a sample and clicking run displays real Swift CLI output in the browser within a few seconds

## 4. LLM Verse Selection — Stage 2

- [x] 4.1 Create `app/providers/gemini.py` — thin async client for Gemini Flash (`generativelanguage.googleapis.com`), accepts system + user prompt, returns JSON string
- [x] 4.2 Create `app/lookup/base.py` — dataclasses `LookupRequest`, `LookupResult`, `Reference`; `LookupAdapter` Protocol with `app_variant: str` and `select(req) -> LookupResult`
- [x] 4.3 Create `app/lookup/christian.py` — implements `LookupAdapter`, holds Christian verse-pick system prompt, calls Gemini via `gemini.py`, parses JSON output into `LookupResult`
- [x] 4.4 Ensure Christian prompt enforces: exactly 1 primary + 2 alternates, `ref` format validation, `shortReason` 1-3 sentences plain English, no verse text in output
- [x] 4.5 Create `app/lookup/stoic.py` — stub adapter returning a clear "not yet implemented" `LookupResult`
- [x] 4.6 Add variant resolution in `POST /run` — reads `variant` from form/body, maps to adapter instance
- [x] 4.7 Add crisis keyword list (`["suicide", "self-harm", "hurt myself", "kill myself", "end it all"]`) in `app/pipeline.py`
- [x] 4.8 Implement crisis detector: scans `anonymizedText` for keywords, sets `crisisFlag: bool` on `SentimentResult`
- [x] 4.9 Update `result.html` with crisis banner (visible only when `crisisFlag` is true), verse references section showing `primary` + `alternates`
- [x] 4.10 Verify end-to-end: pick sample → run → see anonymized text + sentiment + lookup result within ~5-10 seconds (verse text requires GEMINI_API_KEY)
- [x] 4.11 Verify Stoic toggle returns stub message instead of crashing
