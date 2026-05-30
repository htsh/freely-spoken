# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

`AGENTS.md` is a parallel instruction file used by OpenCode and mirrors this file. Keep architectural guidance in sync across both when you change one.

## Project

iOS-only Expo / React Native app that records audio, transcribes it on-device with Apple Speech, and runs sentiment + emotion classification plus transcript anonymization through Apple's on-device Foundation Models LLM. Only the on-device-anonymized text + sentiment metadata leave the device, to a hosted FastAPI backend (`server/`) that picks a canonical reference (a Bible verse for the Christian variant) and fetches the canonical text from a trusted source. There is no Android support, no persistent storage, no chat or session memory.

## Branding

The Christian version of this app is being released as **Freely Spoken** (display name: "Freely Spoken", handle/bundle ID slug: `freelyspoken`). The domain `freelyspoken.com` is secured. The current repo name (`mic-check`) is a working name and may be renamed to match later. When writing copy, UI strings, or App Store metadata for the Christian variant, use "Freely Spoken" as the product name.

The Buddhist version (v3, the Dhammapada variant — internal `appVariant: "dhammapada"`) is being released as **Idle Ashes**. Domain `idleashes.com` to be secured. When writing copy, UI strings, or App Store metadata for the Buddhist variant, use "Idle Ashes" as the product name. The internal `appVariant` value stays `"dhammapada"` (it names the corpus, not the product). See `docs/idle-ashes-overview.md` for a human-oriented walkthrough of the data-prep and labeling work.

## Commands

Device app:

```bash
npm install
npx expo prebuild           # regenerates ios/ (gitignored) — required after dependency or app.json changes
npx expo run:ios --device   # build native project, install on connected device, launch
npm run lint                # eslint via expo-config
npm run typecheck           # tsc --noEmit
npm test                    # vitest (sentiment-parsing unit tests)
```

CI (`.github/workflows/ci.yml`) runs two jobs on every push/PR to `main`: `check` (device lint + typecheck + vitest) and `server` (hermetic `pytest` for the FastAPI adapter suite — no network/keys, the LLM call is stubbed).

### Build variants (product flavors)

One codebase ships as multiple App Store apps, selected at build time by `EXPO_PUBLIC_APP_VARIANT` (`christian` → **Freely Spoken**, `dhammapada` → **Idle Ashes**, `stoic` → unreleased stub). `app.config.js` is the dynamic Expo config: it reads the variant and overrides native identity (display name, `ios.bundleIdentifier`, `android.package`, URL `scheme`, icon) and rewrites the product name inside every permission string, over the static `app.json` base (which is the Christian/Freely Spoken default). The runtime JS reads the same variant via `getBuildAppVariant()` (`services/lookup-request.ts`). **Do not put variant identity back into `app.json`** — it stays the base; per-variant overrides live in `app.config.js` `VARIANTS`.

```bash
# local device run
npx expo run:ios --device                                   # Freely Spoken (default)
EXPO_PUBLIC_APP_VARIANT=dhammapada npx expo run:ios --device # Idle Ashes

# EAS builds (profiles in eas.json; *-idleashes set the variant env)
eas build --profile production               # Freely Spoken
eas build --profile production-idleashes     # Idle Ashes
```

Each variant is a separate App Store entry (own bundle id, icons, screenshots, privacy label). The Idle Ashes bundle ids in `app.config.js` are placeholders under the existing `com.htsh` namespace and need real Apple identifiers (and likely its own EAS project id) before its first store build; a dedicated Idle Ashes icon/splash is still TODO (falls back to the shared icon). The backend stays one shared deployment that dispatches by `appVariant` — variants are not separate servers.

Server (`server/`, FastAPI deployed to Fly.io):

```bash
cd server
cp .env.example .env        # fill GEMINI_API_KEY, OPENROUTER_API_KEY, GROQ_API_KEY, LOOKUP_CLIENT_SECRET
pip install -e .
uvicorn app.main:app --reload --port 8080
```

See `server/README.md` for the full endpoint contract, env-var table, and Fly deploy notes.

Vitest covers sentiment-parsing utilities (`hooks/__tests__/`). End-to-end verification still relies on `tools/sentiment-cli/` (prompt sweeps), `tools/lookup-harness/` (selection prompts + provider behavior), and device runs — see `docs/debug-testing.md` for the matrix.

This app **cannot run in Expo Go** — it depends on three native modules (`expo-av`, `expo-speech-recognition`, `@ratley/react-native-apple-foundation-models`). Always go through `expo run:ios --device`. Simulators won't help: `requiresOnDeviceRecognition: true` and Apple Intelligence both need real hardware (iPhone 15 Pro / 16 series, iOS 26+, Apple Intelligence enabled in Settings).

`/ios` and `/android` are gitignored — they're regenerated by `expo prebuild`. Never edit native files expecting them to persist; configure via `app.json` plugins instead (see the `expo-av` / `expo-speech-recognition` plugin entries that declare the permission strings).

## Architecture

The whole user flow is one screen (`app/index.tsx`) driving an `idle → recording → processing → responseLookup → results` state machine. Each step is a hook that owns its own state; `index.tsx` wires them together via `useEffect`s that chain the pipeline:

1. `useAudioRecorder` (`hooks/use-audio-recorder.ts`) — wraps `expo-av`'s `Audio.Recording`, returns `{ duration, startRecording, stopRecording }`. Holds the recording in a ref and tears it down on unmount.
2. `useTranscriber` (`hooks/use-transcriber.ts`) — feeds the recorded URI to `ExpoSpeechRecognitionModule.start({ audioSource: { uri }, requiresOnDeviceRecognition: true })` and listens via `useSpeechRecognitionEvent('result' | 'end' | 'error')`. Returns `{ transcript, isTranscribing, error, transcribe, reset }`. The hook has no return value from `transcribe()` — results arrive asynchronously through events and update hook state.
3. `useSentimentAnalyzer` (`hooks/use-sentiment-analyzer.ts`) — calls Apple Foundation Models for sentiment, emotions, confidence, and anonymized text. Returns `{ result, raw, isAnalyzing, error, analyze, reset }`. The `raw` field (`{ strategy: 'object' | 'text-fallback', value: string }`) captures pre-normalization output and the generation path taken — used by the debug screen. See below.
4. `useSpiritualResponseLookup` (`hooks/use-spiritual-response-lookup.ts`) — POSTs the anonymized text + sentiment metadata + `appVariant` to the hosted backend via `services/lookup-client.ts`, gets back `{ primary, alternates, provider, model, retryCount, fallbackUsed, crisisFlag }` (or a Stoic stub). One shot per call, no retries on device — the backend owns provider fallback. Returns `{ result, isLoading, error, lookup, reset }`.

The `processing` state covers transcription + sentiment; `responseLookup` is the off-device network step (separated so loading copy + error handling are explicit). Three effects in `app/index.tsx` advance the machine: transcript done → run sentiment; sentiment done → run lookup; lookup settled → render results. If you add a new pipeline step, follow the same pattern: a hook with `{ result, isX, error, run, reset }` plus an effect in `index.tsx`.

`docs/architecture-review-2026-05-16.md` is the most recent deepening review — read it before broad refactors to the sentiment pipeline, state machine, or privacy guard.

### Privacy boundary

The on-device side runs sentiment + anonymization with Apple Foundation Models. **Only the anonymized text + sentiment metadata (`{appVariant, anonymizedText, sentiment, emotions, confidence}`) leave the device.** No audio, transcript, audio file path, recording duration, or device identifiers are ever sent. The lookup client (`services/lookup-client.ts`) is the only network egress in the app — anything new that hits the network goes through there or it breaks the privacy posture.

### Hosted backend (`server/`)

FastAPI service deployed to Fly.io. Sole endpoint that does work is `POST /lookup`. Receives the anonymized payload, scans for crisis keywords (informational `crisisFlag` only — no LLM prompt branching), dispatches by `appVariant` to a registered adapter:

- **Christian** (`server/app/lookup/christian.py`) — LLM picks 1 primary + 2 alternate Bible references, server fetches canonical verse text from the configured Bible API (`server/app/lookup/bible_api.py`, default `bible-api.com`, World English Bible) for each reference before responding. LLM output is never returned as scripture text. Per-reference Bible API failures populate `textError`; the whole response only fails when _every_ fetch fails.
- **Stoic** — stub adapter returns `{ status: "not_implemented", appVariant: "stoic" }` until the catalog is seeded.

Provider chain default is Gemini Flash → OpenRouter free → Groq, configurable via `LOOKUP_PROVIDER_ORDER`. The runner registry in `server/app/llm_runner.py` also supports Cloudflare, Together, and Cerebras — selectable by listing them in the env var. Providers do one-shot calls and raise typed errors; the runner handles immediate fallback on 429, bounded jittered retries on transient failures, and `AllProvidersFailedError` when the chain is exhausted.

Device config lives in `app.json` `extra` (`lookupApiUrl`, `lookupClientSecret`, `appVariant`), sourced from `EXPO_PUBLIC_LOOKUP_API_URL` / `EXPO_PUBLIC_LOOKUP_CLIENT_SECRET` / `EXPO_PUBLIC_APP_VARIANT` at build time. If `lookupApiUrl` is unset, the device throws `MissingLookupApiUrlError` before any network call — this is also the emergency-rollback path (a build without the URL falls back to the previous on-device-only flow).

The Mac-local harness (`tools/lookup-harness/`) is still the right place to iterate prompts and provider behavior — faster cycle than redeploying. The production code lives in `server/`. **When changing prompts or adapters, port the change to both** (or document the divergence intentionally). Treat `server/` as the source of truth for production behavior.

**Free chain is primary.** Home GPU is planned as last-resort overflow only — see `docs/superpowers/home-gpu-overflow-plan.md` for the 3060/3090 Ti setup. Don't propose wiring it in until the free-tier providers prove insufficient.

### Planned hosted response direction

The next product direction is **three ordered versions**, each sharing the privacy-first pipeline (record → transcribe → analyze/anonymize on device; only anonymized text leaves the device) and differing only in the response layer:

1. **Christian (v1)** — first commit. LLM selects a Bible verse reference; app fetches canonical verse text from a Bible API.
2. **Stoic (v2)** — second commit. LLM selects a passage ID from a curated Stoic catalog (Epictetus _Enchiridion_ + Marcus Aurelius _Meditations_); backend returns stored canonical text. Catalog curation and response framing are governed by `docs/stoic-curation-rubric.md` — the "Stoic but not bro-Stoic" rules are load-bearing for this version's tone.
3. **Dhammapada (v3)** — committed. LLM selects a Dhammapada passage ID from a backend-owned curated catalog (423 verses); server returns canonical text from the catalog. Catalog uses LLM-assisted labeling with human review under a frozen rubric/vocabulary. Crisis-flag hard-excludes high-risk passages from the catalog index *before* the LLM sees it — stricter than the Christian variant's informational-only crisis flag. Source/rights review is a strict gate before any labeling or adapter work. The labeling pipeline + driver live in `tools/dhammapada-labeling/` (dev-only data prep, not runtime); the offline labeling model is **deepseek-v4-pro** (chosen in `openspec/changes/dhammapada-catalog-lookup/provider-eval-results.md`; allowed to differ from the runtime selector chain). First-pass labels for all 423 verses are generated and backed up under `tools/dhammapada-labeling/labeled/` — this is a **pre-review intermediate** (`reviewedBy: null`); it is promoted to the runtime catalog `server/app/lookup/dhammapada_catalog.json` only after human review (task 2.8). See `openspec/changes/dhammapada-catalog-lookup/` for the in-flight plan and `docs/other_wisdom_sources.md` for v4+ candidates (Tao Te Ching, Pirkei Avot, Analects).

The product shape v1 and v2 are pulling toward is **"short, concrete passage."** This is a provisional criterion — validate it against real responses before treating it as decided.

Implementation guidance for upcoming hosted lookup work:

- Keep lookup single-turn. Do not add chat memory, thread state, accounts, feeds, or persistent history.
- Keep shared infrastructure separate from version-specific behavior with an explicit `appVariant: "christian" | "stoic" | ...` boundary or equivalent.
- Use the hosted LLM for relevance/reference selection, not as the source of canonical passage text.
- Version-specific layers own their prompts, response copy, content constraints, and canonical-text source (Bible API for Christian, stored catalog for Stoic+).
- Provider order: Gemini Flash free tier first, OpenRouter free models as fallback, immediate fallback on `429`, bounded retries with jitter for transient errors.
- Return one focused response plus structured metadata: source/reference, text, provider, model, retry count, fallback-used flag.
- Optional read-aloud may be added for fetched canonical text, never provider-generated text.
- Do not broaden to additional traditions unless a future plan explicitly changes that.

A working prototype of this backend already exists at `tools/lookup-harness/` — see the entry under "Debug tools" below. Iterate selection prompts and provider behavior there before phone-side implementation. Original plan: `docs/plans/2026-05-13-lookup-harness-plan.md`.

### Sentiment analyzer and anonymizer (the non-obvious part)

`useSentimentAnalyzer.analyze()` first checks `getTextModelAvailability()` and throws a readable error if Apple Intelligence is unavailable. It then tries **two strategies in order**:

1. `generateObject()` with a JSON schema for `{ sentiment, emotions, confidence, anonymizedText }`.
2. On any failure, falls back to `generateText()` and parses with `extractFirstJSONObject()` — a hand-written brace matcher that tolerates strings, escapes, and surrounding prose from the model.

Both paths funnel through `normalizeSentiment` / `normalizeEmotions` / `normalizeConfidence` / `normalizeAnonymizedText`. These exist because the on-device 3B model is loose with labels — it returns `"angry"`, `"happy"`, `"calm"`, percentages like `"85%"`, comma-joined emotion strings, etc. The `SENTIMENT_ALIASES` and `EMOTION_ALIASES` maps coerce these to the canonical `SENTIMENTS` / `EMOTIONS` enum values that the UI renders. `normalizeAnonymizedText` applies a local privacy guard against the source transcript and falls back to a generic category-based sentence, never the original transcript, if the model omits the field, repeats protected terms, includes obvious identifiers, or stays too close to the source. **When changing prompts or model packages, run real recordings end-to-end** — schema validation alone won't catch normalization or privacy regressions.

Pure parsing (`normalizeSentiment`, `normalizeEmotions`, `normalizeConfidence`, `extractFirstJSONObject`, alias maps) lives in `hooks/sentiment-utils.ts` — RN-free so vitest can cover it. The hook owns the FM calls and orchestration; land parser changes in `sentiment-utils.ts` and extend the test suite in `hooks/__tests__/`.

`docs/on-device-ai-approach.md` and `docs/foundation-models-packages.md` capture the rationale for choosing `@ratley/react-native-apple-foundation-models` over the alternatives (`@react-native-ai/apple`, `react-native-apple-llm`, `react-native-apple-intelligence`) and the longer-term server-fallback / Android plan. Read these before swapping the FM package.

## Debug tools (dev-only)

Off-device affordances for iterating without recording on a phone:

- **`/debug` route** (`app/debug.tsx`) — `__DEV__`-gated link on the home screen. Bypasses recording + STT: type a transcript, hit Analyze, and see the normalized sentiment/emotions, anonymized text, and raw model output, with a badge showing whether `generateObject` succeeded or the `generateText` fallback fired. Run it in the iOS 26 Simulator on an Apple Silicon Mac with Apple Intelligence enabled.
- **`tools/sentiment-cli/`** — Swift Package executable that calls `FoundationModels` directly on macOS. `swift run sentiment-cli "text"` (or pipe stdin); `--raw` also dumps unstructured `generateText` output. Useful for prompt sweeps over fixture files. The prompt and `Generable` schema are duplicated from `use-sentiment-analyzer.ts` — keep them in sync when changing the production prompt.
- **`tools/sentiment-cli/run-anonymization-samples.sh`** — runs 20 privacy-heavy samples through the Swift CLI with `--raw`. Use this to catch privacy guard regressions after changing anonymization rules.
- **`tools/lookup-harness/`** — Mac-local FastAPI web app (`./start.sh`, http://localhost:8000) that exercises the text half of the production pipeline: shells out to the Swift `sentiment-cli` for sentiment + anonymization, then calls a hosted provider for passage selection. This is the intended place to iterate selection prompts before phone-side implementation.
  - `app/pipeline.py` — Swift CLI subprocess wrapper + crisis-language scan
  - `app/providers/{gemini,openrouter,groq}.py` — async clients; selectable per-run via UI dropdown
  - `app/lookup/{base,christian,stoic}.py` — `LookupAdapter` Protocol; one adapter per `appVariant`. Stoic is a stub until the catalog is seeded
  - Fallback chain (UI checkbox): primary → next provider on `429` / timeout, with bounded retries + jitter. This mirrors the provider strategy planned for the device app
  - API keys via `.env` (`GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `GROQ_API_KEY`); missing keys produce a clean lookup error rather than crashing the run

The Swift CLI mirrors the anonymized-text guard and prints both raw model output and guarded anonymized text. Keep the CLI and TypeScript guard rules in sync when changing privacy behavior.

Release/TestFlight builds must not expose debug affordances: no `/debug` access, raw transcript, sentiment JSON, guarded-anonymous debug block, provider/model name, fallback status, or retry count in the app UI.

See `docs/debug-testing.md` for the full test matrix, fixture workflows, end-to-end device checklist, and the prompt/schema change checklist (the 5-step sequence to follow when editing `SENTIMENT_PROMPT`, `SENTIMENT_SCHEMA`, aliases, or anonymization rules).

## Conventions

- TypeScript strict mode. Path alias `@/*` maps to repo root (`@/hooks/...`, `@/components/...`).
- Named exports everywhere — hooks and components use `export function useX()` / `export function X()`, imported as `import { X } from '@/path'`. No default exports outside of `app/` route files (which expo-router requires).
- Routing is `expo-router` file-based (`app/_layout.tsx` is the root Stack, `app/index.tsx` is the home screen). `typedRoutes` and `reactCompiler` are both enabled in `app.json`.
- New Architecture is on (`newArchEnabled: true`) — required by the Foundation Models bridge.
- Theming goes through `ThemedText` / `ThemedView` + `useThemeColor` against `constants/theme.ts`. Match this pattern instead of hardcoding colors when adding new UI.

## Agent skills

### Issue tracker

Issues live as GitHub issues in `htsh/mic-check`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default canonical labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout (`CONTEXT.md` + `docs/adr/` at repo root, populated lazily — neither exists yet; proceed silently if absent). See `docs/agents/domain.md`.

### Launch artifacts

`docs/testflight-launch-checklist.md` and `docs/privacy-policy.md` are load-bearing for the App Store / TestFlight push for **Freely Spoken**. Update both when changing data-collection behavior or release scope.

## OpenSpec workflow

This repo uses an experimental OpenSpec change-management workflow for larger changes. The `/openspec-propose`, `/openspec-apply`, `/openspec-explore`, and `/openspec-archive` skills drive the `openspec` CLI through structured artifacts (`proposal.md`, `design.md`, `tasks.md`) under `openspec/`. Use this workflow when the user invokes one of those commands or asks to propose, apply, or archive an OpenSpec change. The parallel `opsx-*` commands in `.opencode/commands/` are the OpenCode-side mirror.
