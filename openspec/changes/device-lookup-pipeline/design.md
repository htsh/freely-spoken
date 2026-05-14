## Context

The on-device PoC is complete: `idle → recording → processing → results`, with sentiment + anonymization running on Apple Foundation Models. The Mac-local harness (`tools/lookup-harness/`) has proven the contract for verse selection (Gemini → OpenRouter/Groq fallback) and canonical text fetch (bible-api.com). What it has not proven: a real device hitting a real hosted backend with the anonymized payload, displaying canonical scripture text in the results screen.

This change closes that gap for Christian v1. The architecture is dictated by the privacy posture (only anonymized text + sentiment metadata leave the device) and the canonical-text rule (LLM picks references, never generates scripture). The harness adapter code is the reference implementation but is not directly reusable — the harness shells out to a Mac-only Swift CLI for sentiment, while the device runs sentiment locally and sends the result to the backend. So the backend is a slimmer service: no Swift, no sentiment, no Apple Intelligence dependency.

## Goals / Non-Goals

**Goals:**

- Device app makes one HTTPS call per recording with anonymized text + sentiment metadata, and displays a canonical Bible verse + 2 alternates in the results screen.
- Hosted backend is deployable to a low-end VPS, has zero dependency on Apple Intelligence or any Mac-only tooling, and exposes a stable `POST /lookup` contract that survives Stoic v2.
- Variant boundary (`appVariant: "christian" | "stoic"`) is wired end-to-end from device → backend → adapter, with Stoic returning a clear stub so adding a real Stoic adapter is a backend-only change.
- Backend never returns LLM-generated scripture text — canonical text always comes from the Bible API.
- Provider fallback (Gemini → OpenRouter → Groq) and crisis-keyword scan move from the harness into the deployable service with the same observable behavior.
- Hosted backend can be swapped for a self-hosted Bible API mirror later without code changes (config-only).

**Non-Goals:**

- No Stoic content. Stoic adapter is a stub; corpus seeding is a separate change.
- No auth, accounts, rate limiting, multi-tenancy, persistent history, or analytics beyond stdout logging.
- No translation picker UI. Server picks one default translation (World English Bible); device displays the translation name returned by the API.
- No read-aloud of the verse in v1. Optional and easy to add later since canonical text comes from a trusted source.
- No Android, no simulator support for the device path (sentiment still requires real hardware + Apple Intelligence).
- No streaming response, no SSE, no websockets — a single POST/response.
- No on-device caching of past lookups. Single-shot, ephemeral, matches the privacy posture.

## Decisions

| Decision                  | Choice                                                                                                              | Rationale                                                                                                                                                                                                                                                                       |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend framework         | FastAPI in a new top-level `server/` directory                                                                      | Matches the harness so prototype → prod port is mechanical. Async fits the Gemini + Bible API I/O overlap. New top-level dir (not a subfolder of `tools/`) signals it is production code, not a dev tool. Rejected: reusing `tools/lookup-harness/` (mixes dev + prod concerns). |
| Backend hosting           | Fly.io (single small VM, free tier sufficient)                                                                      | Fast deploy from Dockerfile, free TLS, low ops surface. Rejected: Vercel/Render free tiers sleep on idle (cold start is unacceptable for a single-shot UX); raw VPS adds undifferentiated ops; Cloud Run requires a billing account up front.                                   |
| Device → backend URL      | `LOOKUP_API_URL` from `expo-constants` `extra`, baked at build time                                                 | Single source of truth, swappable per environment via `app.json` + `EXPO_PUBLIC_*` or build profile. No runtime config UI needed for v1.                                                                                                                                        |
| Backend response shape    | `{ primary: Ref, alternates: [Ref, Ref], provider, model, retryCount, fallbackUsed, crisisFlag }`                   | Matches the harness JSON shape so the device contract has already been exercised. Each `Ref = { ref, text, translation, shortReason, textError? }` — `textError` is present when Bible API fetch failed for that one reference, so the lookup remains useful.                   |
| Bible API client          | Reuse harness logic, productionize as `server/bible_api.py`                                                         | Same default URL/translation, same per-process cache, same env vars (`BIBLE_API_URL`, `BIBLE_TRANSLATION`). Cache is per-process; restart clears it — fine for v1.                                                                                                              |
| Canonical text guarantee  | Server fetches verse text from Bible API for every reference before responding; LLM output is references-only       | The single hard rule of the product. Belt-and-suspenders: backend also strips any quoted scripture from `shortReason` before responding. Rejected: trusting LLM not to include scripture (it sometimes does).                                                                   |
| Provider fallback         | Gemini Flash → OpenRouter free → Groq; immediate fallback on `429`, bounded retries with jitter for transient codes | Matches harness, matches `project_direction.md`. Fallback chain and retry policy controlled by env (`LOOKUP_PROVIDER_ORDER`, `LOOKUP_MAX_RETRIES`).                                                                                                                             |
| Crisis handling           | Backend computes `crisisFlag` from a keyword list against anonymized text; device shows a non-blocking banner       | Visibility without coupling LLM behavior or product UX to a naive keyword list. The flag is data; the device decides UI treatment. Rejected: backend swapping in a different LLM prompt for flagged inputs (premature and hard to test).                                        |
| Device hook shape         | `useSpiritualResponseLookup` returning `{ result, isLoading, error, lookup, reset }`                                | Mirrors `useSentimentAnalyzer` / `useTranscriber` exactly so `app/index.tsx` can wire it with the same effect-chain pattern. New hires read one hook, they read them all.                                                                                                       |
| State machine extension   | New `responseLookup` state inserted between `processing` and `results`                                              | `processing` is "on-device" (transcribe + sentiment); `responseLookup` is "off-device" (network call). The split makes loading copy + error handling clearer than a single `processing` state covering both.                                                                    |
| Device retry policy       | No retries on device — backend owns fallback + retries                                                              | Avoids two retry layers fighting each other. If the backend gives up, the device shows the error and a "try again" button (manual user action).                                                                                                                                 |
| Variant boundary location | Backend dispatches by `appVariant` to an adapter; device sends the variant in the request                           | Single dispatch point on the backend means adding Stoic v2 doesn't touch device code. Device still has `appVariant` so the results screen can branch on copy / branding when the time comes.                                                                                    |
| Stoic stub                | Stoic adapter returns HTTP 200 with `{ status: "not_implemented", appVariant: "stoic" }` shape                      | The variant boundary is exercised in real network calls. Rejected: 501 status (couples HTTP semantics to product not-yet-shipped logic) and frontend-only stub (variant routing wouldn't be tested end-to-end).                                                                  |
| Error surfacing           | Backend returns structured errors `{ error: { code, message } }`; device shows `message` verbatim                   | One round-trip means errors are part of the UX. `code` is for machine handling (e.g. `bible_api_down`, `all_providers_failed`, `unknown_variant`); `message` is human-readable.                                                                                                  |
| Backend secrets           | `.env` on the VM with `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `GROQ_API_KEY`; Fly secrets for production            | Keys never on device. Missing keys produce a clean error from that provider so fallback can move past it. Rejected: a single shared key — provider keys have different rate-limit profiles, mixing them blocks observability.                                                   |
| Logging                   | Backend logs to stdout with structured JSON (request id, provider, retry count, fallback flag, latency)             | Fly captures stdout to its log drain; no log infra to build. No PII logged: only sentiment label, emotion list, confidence — never the anonymized text body. Rejected: logging the anonymized text (still upsetting if leaked, even though anonymized).                          |
| Bible translation default | World English Bible (`web`), env-overridable                                                                        | Public domain, no licensing risk, supported by bible-api.com out of the box. Translation picker UI is a separate change.                                                                                                                                                        |

## Risks / Trade-offs

- **[Risk]** bible-api.com is described as a hobby service with a per-IP rate limit. Heavy traffic could trigger 429s for every user behind the same egress IP. → **Mitigation**: per-process cache for repeat refs; document that `BIBLE_API_URL` can point at a self-hosted mirror. If we hit limits in practice, swap to a mirror — config change only.
- **[Risk]** Gemini → OpenRouter → Groq fallback chain means a single user request can make 4-9 outbound calls (3 providers × up to 3 retries) and inflate p99 latency. → **Mitigation**: bounded retries with jitter capped to keep total backend time under ~15 seconds; if exceeded, return a clean error. Device shows a single loading state for the whole call.
- **[Risk]** Anonymization runs on-device with the 3B Foundation Models — occasional leakage of PII into `anonymizedText` is possible (the TS guard catches obvious cases, but not all). That text leaves the device. → **Mitigation**: the privacy guard in `use-sentiment-analyzer.ts` already falls back to a generic category sentence on suspected leakage. Re-verify the guard with the anonymization sample script before shipping the device build. Backend does not log the body.
- **[Risk]** Crisis keyword list is naive and will both miss real crisis language and false-positive on harmless phrasing. → **Mitigation**: `crisisFlag` is informational only in v1 (banner, no gating). When real product treatment is added (likely at Stoic v2 per the project doc), replace the keyword list with something better.
- **[Risk]** All requests are anonymous; nothing prevents abuse of the hosted backend (LLM and Bible API cost). → **Mitigation**: deploy with an app-attest or per-build API key header (`LOOKUP_CLIENT_SECRET`) the device adds to every request. Not full security, but enough to keep random callers off the endpoint. Cap concurrent in-flight requests on the server with a semaphore.
- **[Risk]** The harness and production backend will diverge over time, leading to "works in harness, fails in prod" surprises. → **Mitigation**: keep the harness as the *iteration* tool for prompts and provider behavior, but consider the production code path the source of truth. When a prompt or adapter changes in the harness, port it to `server/` in the same PR (or document the divergence intentionally).
- **[Risk]** Fly.io free tier may not remain free or may add cold-start behavior. → **Mitigation**: backend is one container with no DB; migrating to another host (Railway, Render paid, DO App Platform) is a deploy-file change. Don't lock in to Fly-specific features.

## Migration Plan

1. **Backend first, behind a feature flag in the device build**:
   - Build `server/` locally; verify with the existing harness fixtures that responses are byte-equivalent for the Christian flow (modulo timing/provider).
   - Deploy to a Fly app at a non-public hostname (e.g. `mic-check-lookup.fly.dev`); smoke test with `curl`.
   - Add `LOOKUP_API_URL` to `app.json` `extra`, default unset; absence disables the responseLookup step (device falls back to current `results` state).
2. **Device integration on a branch**:
   - Add hook, state, results UI behind a `__DEV__` toggle or a build profile env var, so the previous flow still ships if needed.
   - Test on a real device (iPhone 15 Pro / 16 series + Apple Intelligence) with the deployed backend.
3. **Cutover**:
   - Once a stable build runs the full pipeline end-to-end against the deployed backend, remove the dev-only toggle and ship.
4. **Rollback**:
   - Device side: a build without `LOOKUP_API_URL` set in `extra` is the previous flow — no code revert needed for emergency rollback if we keep that branch in place for the first release.
   - Backend side: Fly keeps prior image; redeploy the prior tag.

## Open Questions

- **App identity / client secret**: do we ship a per-build `LOOKUP_CLIENT_SECRET` from the start, or do TestFlight builds run unauthenticated? Leaning yes-from-start to keep abuse-by-curl off the endpoint, but it adds one secret to manage.
- **Backend canonicalization of `ref` format**: harness validates `^[1-3]?\s?[A-Za-z]+\s\d+:\d+(-\d+)?$`. Bible API also accepts ranges. Lock to single-verse only, or allow short ranges? Default to single-verse for v1; revisit if model picks ranges often.
- **Should `crisisFlag` ever trigger a different LLM prompt or a different response shape?** Out of scope for v1 per design above, but the spec needs to be explicit that it's currently *just a flag*.
- **Latency budget**: the harness comfortably runs in 3-8s. With provider fallback worst case, the device could see ~15s. Is that acceptable for the first release, or should the device cancel after N seconds and offer retry? Defer; measure first.
- **Bible API mirror**: is the hobby-service rate limit a real risk for our v1 audience size, or are we over-engineering by planning around it? Probably fine for v1; revisit if 429s show up in logs.
