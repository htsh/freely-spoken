## 1. Backend bootstrap

- [x] 1.1 Create `server/` directory at repo root with subdirs `server/app/`, `server/app/lookup/`, `server/app/providers/`
- [x] 1.2 Create `server/pyproject.toml` with FastAPI, Jinja2-not-needed, httpx, python-dotenv, uvicorn, pydantic
- [x] 1.3 Create `server/Dockerfile` (slim python base, copy app, install deps, expose 8080, run `uvicorn app.main:app --host 0.0.0.0 --port 8080`)
- [x] 1.4 Create `server/.env.example` with `GEMINI_API_KEY=`, `OPENROUTER_API_KEY=`, `GROQ_API_KEY=`, `LOOKUP_CLIENT_SECRET=`, `BIBLE_API_URL=`, `BIBLE_TRANSLATION=`, `LOOKUP_PROVIDER_ORDER=`, `LOOKUP_MAX_RETRIES=`
- [x] 1.5 Create `server/README.md` with local-run, env-var, and deploy notes

## 2. Backend HTTP layer (`lookup-backend-api`)

- [x] 2.1 Create `server/app/main.py` — FastAPI app, structured stdout JSON logging, request-id middleware
- [x] 2.2 Create `server/app/schemas.py` — Pydantic models for `LookupRequest`, `Reference`, `LookupResult`, `StoicStubResult`, `ErrorBody`
- [x] 2.3 Implement `POST /lookup` handler: validate body, enforce `LOOKUP_CLIENT_SECRET` header when set, dispatch by `appVariant`
- [x] 2.4 Implement structured error responses (`unknown_variant`, `invalid_request`, `unauthorized`, `all_providers_failed`, `bible_api_down`, `internal_error`) with consistent `{ error: { code, message } }` shape
- [x] 2.5 Add request-scoped logger that emits one structured log line per request with request id, variant, sentiment, emotions, confidence, provider, model, retry count, fallback flag, crisis flag, and latency — never the anonymized text body
- [x] 2.6 Add `GET /healthz` returning `{ ok: true }` for uptime checks
- [x] 2.7 Add concurrency cap via a single global asyncio semaphore (configurable env var `LOOKUP_MAX_CONCURRENCY`)

## 3. Providers and fallback chain

- [x] 3.1 Port `app/providers/gemini.py` from the harness to `server/app/providers/gemini.py`; bounded retries with jitter for 5xx and transient errors; raise typed `GeminiError`
- [x] 3.2 Port `app/providers/openrouter.py` to `server/app/providers/openrouter.py` with the same retry/error shape
- [x] 3.3 Port `app/providers/groq.py` to `server/app/providers/groq.py` with the same retry/error shape
- [x] 3.4 Read `LOOKUP_PROVIDER_ORDER` (default `"gemini,openrouter,groq"`) and `LOOKUP_MAX_RETRIES` at startup into a single config module
- [x] 3.5 Implement provider runner that walks the order list, immediate-fallback on 429, retries other transient errors, surfaces `all_providers_failed` after the chain is exhausted

## 4. Christian lookup flow (`christian-lookup-flow`)

- [x] 4.1 Create `server/app/lookup/base.py` with `LookupRequest`, `LookupResult`, `Reference` dataclasses and a `LookupAdapter` Protocol (`app_variant: str`, `async select(req) -> LookupResult`)
- [x] 4.2 Port `bible_api.py` from the harness to `server/app/lookup/bible_api.py`; per-process cache keyed by `(ref, translation)`; honor `BIBLE_API_URL` and `BIBLE_TRANSLATION`
- [x] 4.3 Create `server/app/lookup/christian.py` — port the system prompt, JSON extraction, reference validation, and `_enrich_with_text` from the harness; reject responses that contain extended scripture text in `shortReason`
- [x] 4.4 Wire Christian adapter into the variant registry (live verification deferred to Group 12 — requires real Gemini key)
- [x] 4.5 Ensure individual Bible API failures populate `Ref.textError` rather than failing the whole response; only return `bible_api_down` when *all* fetches fail

## 5. Variant routing (`variant-routing`)

- [x] 5.1 Create `server/app/lookup/stoic.py` returning `{ status: "not_implemented", appVariant: "stoic", message }` with HTTP 200
- [x] 5.2 Define the variant registry as a `dict[str, LookupAdapter]` populated at app startup; reject unknown variants with `unknown_variant`
- [x] 5.3 Add tests / curl scripts in `server/scripts/` for both variants (christian success, stoic stub, unknown 400)

## 6. Crisis detection

- [x] 6.1 Add crisis keyword list to `server/app/crisis.py` (start with the harness list: `["suicide", "self-harm", "hurt myself", "kill myself", "end it all"]`, plus any additions discovered via harness)
- [x] 6.2 Compute `crisisFlag` from the anonymized text before dispatching to the adapter; pass it through to the response
- [x] 6.3 Confirm `crisisFlag` does not change the LLM prompt or branch the flow — purely informational

## 7. Deployment

- [x] 7.1 Create `server/fly.toml` targeting a small shared VM, single instance, `8080` internal port, `[env]` with non-secret config defaults
- [ ] 7.2 Set production secrets via `fly secrets set GEMINI_API_KEY=… OPENROUTER_API_KEY=… GROQ_API_KEY=… LOOKUP_CLIENT_SECRET=…` (**USER ACTION** — needs Fly CLI auth + provider keys)
- [ ] 7.3 Deploy with `fly deploy`; verify `/healthz` and run a curl smoke test against `/lookup` with a known-good payload (**USER ACTION** — needs Fly CLI auth)
- [ ] 7.4 Document the public hostname and the build-time env var the device should use (**USER ACTION** — depends on deployed hostname)

## 8. Device wiring — config + client (`device-response-lookup`)

- [x] 8.1 Add `LOOKUP_API_URL` and `LOOKUP_CLIENT_SECRET` to `app.json` `extra`, sourced from `EXPO_PUBLIC_LOOKUP_API_URL` / `EXPO_PUBLIC_LOOKUP_CLIENT_SECRET` for local builds
- [x] 8.2 Create `services/lookup-client.ts` — typed `lookupSpiritualResponse(req)` calling `POST /lookup`, reading config from `expo-constants`, attaching client secret header, exporting `LookupRequest`, `LookupResult`, `Reference`, `LookupError` types
- [x] 8.3 Client throws a clearly-named `MissingLookupApiUrlError` before any fetch if `LOOKUP_API_URL` is unset
- [x] 8.4 Client surfaces backend `{ error: { code, message } }` verbatim through a typed `LookupError` (do not retry, do not parse `code` for branching beyond logging)
- [x] 8.5 Confirm request body shape contains *only* `appVariant`, `anonymizedText`, `sentiment`, `emotions`, `confidence` (no transcript, no audio path, no duration, no device IDs)

## 9. Device wiring — hook and state machine (`device-response-lookup`)

- [x] 9.1 Create `hooks/use-spiritual-response-lookup.ts` with `{ result, isLoading, error, lookup, reset }`; mirror the API shape of `use-sentiment-analyzer.ts`
- [x] 9.2 Implement `lookup(req)` to call the lookup client exactly once; set `isLoading`, populate `result`/`error` accordingly
- [x] 9.3 Implement `reset()` to clear `result`, `error`, `isLoading`
- [x] 9.4 Add `'responseLookup'` to the state union in `app/index.tsx` (currently `'idle' | 'recording' | 'processing' | 'results'`)
- [x] 9.5 Add a `useEffect` that transitions `processing → responseLookup` when sentiment finishes and triggers `lookup(...)` with the anonymized text + sentiment metadata + build's `appVariant`
- [x] 9.6 Add a `useEffect` that transitions `responseLookup → results` when the hook resolves (success or error)
- [x] 9.7 On error in `responseLookup`, surface the message in the results screen and add a "Try again" button that calls `lookup(...)` with the same inputs

## 10. Device wiring — results UI (`device-response-lookup`, `variant-routing`)

- [x] 10.1 Extend the results section of `app/index.tsx` to render the primary `Reference` (verse text, translation, short reason) above the existing sentiment block
- [x] 10.2 Render the two alternates in a collapsible `ThemedView` block, each showing ref, text, translation, and short reason
- [x] 10.3 Render a non-blocking banner above the verse content when `result.crisisFlag === true`
- [x] 10.4 When a `Reference.textError` is present, render the ref + short reason with an inline "couldn't fetch verse text" indicator; never substitute LLM-generated text
- [x] 10.5 Branch UI copy on `appVariant` (e.g. heading "A verse for you" for Christian)
- [x] 10.6 Apply `ThemedText` / `ThemedView` and `useThemeColor` for all new UI; no hardcoded colors

## 11. Privacy + crisis verification

- [ ] 11.1 Re-run `tools/sentiment-cli/run-anonymization-samples.sh` against the latest prompts to confirm no privacy regressions before shipping the device build (**USER ACTION** — needs Mac with Apple Intelligence)
- [ ] 11.2 Verify, by inspecting a captured request (e.g. proxy or `console.log` in dev only, removed before merge), that the request body contains no raw transcript, audio path, or device identifiers (**USER ACTION** — needs device build)
- [ ] 11.3 Verify backend logs (Fly tail) for a real device request do not contain the anonymized text body (**USER ACTION** — needs deployed backend + device build)
- [ ] 11.4 Send a known-crisis-keyword sample end-to-end on a device build and confirm the banner renders and the lookup still returns verses (**USER ACTION** — needs device + deployed backend)

## 12. End-to-end verification

- [ ] 12.1 Run `npx expo prebuild && npx expo run:ios --device` on a real Apple-Intelligence-capable device against the deployed backend; complete one recording end-to-end (**USER ACTION**)
- [ ] 12.2 Force a Gemini 429 (e.g. by exhausting quota or setting a bogus key) and verify the response shows `fallbackUsed: true` with another provider (**USER ACTION**)
- [ ] 12.3 Force a Bible API failure (set `BIBLE_API_URL` to a broken host on the backend) and confirm refs render with the "couldn't fetch verse text" indicator (**USER ACTION**)
- [ ] 12.4 Switch the build's `appVariant` to `"stoic"` and confirm the device gracefully renders the not-implemented stub without crashing (**USER ACTION**)
- [ ] 12.5 Verify network panel / proxy capture shows exactly one outbound HTTPS call per recording (**USER ACTION**)

## 13. Docs

- [x] 13.1 Update `CLAUDE.md` and `AGENTS.md` with the new `server/` directory, the new state machine, the new hook, the `LOOKUP_API_URL` config, and the privacy invariants
- [x] 13.2 Add a short "deploy + rollback" note to `server/README.md` mapping the migration plan from `design.md` into concrete commands
- [x] 13.3 Document the relationship between `server/` and `tools/lookup-harness/` (harness = iteration; server = production; port prompt changes to both)
