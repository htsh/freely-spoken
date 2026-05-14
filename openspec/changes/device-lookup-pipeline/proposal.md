## Why

The Mac-local lookup harness (`tools/lookup-harness/`) has proven the contract for "anonymized text + sentiment metadata → ranked Bible references + canonical verse text." It is not reachable from a real phone, depends on a Swift CLI for sentiment that the device runs natively, and is a developer tool — not a deployable service. To ship Christian v1, the iOS app needs to call a hosted backend over the network, receive canonical verse text from a trusted source (never LLM-generated text), and render the response on a new screen. The privacy posture must hold: only the on-device anonymized text and sentiment metadata may leave the device.

## What Changes

- Add a new hosted FastAPI backend (`server/`) deployable to a VPS, exposing `POST /lookup` with the device contract `{appVariant, anonymizedText, sentiment, emotions, confidence}` and returning `{primary, alternates, provider, model, retryCount, fallbackUsed, crisisFlag}`.
- Extract the production-grade pieces of the harness (provider fallback chain, Christian adapter, Bible API client, crisis keyword scan) into the hosted backend. The harness keeps using its in-process copies; production code is its own module tree so the harness can keep iterating without breaking prod.
- Server-side Christian variant: LLM picks 1 primary + 2 alternate Bible references; backend fetches canonical text from the configured Bible API (default `bible-api.com`, World English Bible) for each reference before responding. LLM output is never used as scripture text.
- Wire the `appVariant: "christian" | "stoic"` boundary through the device request, backend dispatch, and adapter selection. Stoic adapter returns a clear `not_implemented` stub so the boundary is exercised end-to-end.
- Provider fallback chain on backend: Gemini Flash (primary) → OpenRouter free → Groq, with immediate fallback on `429` and bounded retries with jitter for transient errors. Same behavior as harness, now in the deployable service.
- Crisis keyword scan on the anonymized text on the backend; `crisisFlag` returned to the device. Device renders a non-blocking banner above results when the flag is set.
- Add device-side state machine extension: `idle → recording → processing → responseLookup → results`. New hook `hooks/use-spiritual-response-lookup.ts` owns the network call and exposes `{ result, isLoading, error, lookup, reset }`, matching the existing hook shape.
- Extend the results screen (`app/index.tsx`) to render the primary reference, its canonical verse text + translation name, short reason, and a collapsible list of the two alternates. Show provider/model/fallback badges from the response metadata. Existing sentiment/emotion display stays.
- Add a `LOOKUP_API_URL` config (read via `expo-constants`) and a single typed `lookupSpiritualResponse()` client in `services/lookup-client.ts`. No retries on the device — the backend owns retry/fallback. Surface backend errors to the user verbatim.

## Capabilities

### New Capabilities

- `lookup-backend-api`: Hosted FastAPI service exposing `POST /lookup`, the request/response JSON contract, provider fallback chain with retries and jitter, crisis-flag passthrough, and the error shape returned to the device.
- `christian-lookup-flow`: Server-side Christian adapter — LLM picks the references, Bible API fetches the canonical text for each reference, response includes primary + 2 alternates with reference, canonical text, translation name, and short reason. LLM-generated text is never returned as scripture.
- `variant-routing`: `appVariant` boundary wired through device request → backend dispatch → adapter selection. Christian is fully implemented; Stoic returns a `not_implemented` stub so the boundary is real end-to-end. Unknown variants return a 400.
- `device-response-lookup`: Device-side pipeline extension — new `responseLookup` state, `use-spiritual-response-lookup` hook with the standard `{ result, isLoading, error, lookup, reset }` shape, results screen rendering verse + alternates + crisis banner, typed lookup client with `LOOKUP_API_URL` config.

### Modified Capabilities

- _(none — `openspec/specs/` is empty; the harness change has not been archived. Even when archived, the harness specs are scoped to a dev-only Mac-local tool and don't share requirements with the deployed service.)_

## Impact

- **New code**:
  - `server/` — FastAPI app, providers, lookup adapters, Bible API client, crisis scan, Dockerfile, deployment notes.
  - `hooks/use-spiritual-response-lookup.ts` — new device hook.
  - `services/lookup-client.ts` — new typed client.
- **Modified code**:
  - `app/index.tsx` — state machine adds `responseLookup`; new effect triggers lookup; results screen renders verse output.
  - `app.json` — add `LOOKUP_API_URL` to `extra` for `expo-constants`.
- **No changes** to existing on-device hooks (`use-audio-recorder`, `use-transcriber`, `use-sentiment-analyzer`). The lookup is appended; the on-device pipeline is unchanged.
- **No changes** to `tools/lookup-harness/` or `tools/sentiment-cli/`. The harness keeps working as a dev iteration loop with its own in-process code.
- **External dependencies**: backend calls Gemini, OpenRouter, Groq, and `bible-api.com` (or a configured self-hosted replica). API keys live in server env, never on device.
- **Network surface**: device makes one outbound HTTPS call per recording (anonymized text + sentiment metadata only). No audio, no transcript, no PII leaves the device.
- **Deployment**: a deployable VPS service is in scope; concrete hosting (Fly.io / Railway / DO droplet) chosen in `design.md`. Hosting cost is one new ongoing line item.
- **Out of scope**: Stoic content, Bible translation picker UI, read-aloud, account/auth, persistent history, multi-turn chat, Android.
