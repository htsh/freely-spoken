# Repository Guidelines

Note: `CLAUDE.md` is a parallel instruction file for Claude Code. This file is the primary reference for OpenCode sessions. Keep architectural guidance in sync across both when you change one.

## Project

`mic-check` is an iOS-only Expo / React Native app released as **Freely Spoken** (`freelyspoken.com`). It records audio, transcribes it on-device with Apple Speech, analyzes sentiment/emotions and produces anonymized text with Apple's on-device Foundation Models LLM, then calls a hosted FastAPI backend (`server/`) with just the anonymized text + sentiment metadata to receive a canonical response (a Bible verse for the Christian variant). No Android, no web target, no persistent storage, no chat or session memory.

This app **cannot run in Expo Go**. It depends on native modules for audio, speech recognition, and Foundation Models, so use native iOS builds. Apple Intelligence requires real hardware (iPhone 15 Pro/16 series, M1+ iPad/Mac), iOS 26+, and Apple Intelligence enabled in Settings. Simulators won't work for the full recording+transcription flow.

## Commands

```bash
npm install
npx expo prebuild           # regenerates ios/ (gitignored) — required after dependency or app.json changes
npx expo run:ios --device   # build native project, install on device, launch
npm run lint                # eslint via expo config (expo lint)
npm run typecheck           # tsc --noEmit
npm test                    # vitest (sentiment-parsing unit tests)
```

CI (`.github/workflows/ci.yml`) runs lint + typecheck + vitest on every push/PR to `main`.

```bash
# Server (server/, FastAPI, deployed to Fly.io)
cd server && cp .env.example .env   # fill GEMINI_API_KEY, OPENROUTER_API_KEY, GROQ_API_KEY, LOOKUP_CLIENT_SECRET
pip install -e .
uvicorn app.main:app --reload --port 8080
```

- `ios/` and `android/` are gitignored. Do not make durable app changes inside generated native projects.
- `app.config.js` resolves `EXPO_PUBLIC_*` env vars into `app.json extra` at build time. Change env config there, not in `app.json` extras directly (which hold literal `$EXPO_PUBLIC_*` placeholder strings).
- Vitest covers sentiment-parsing utilities (`hooks/__tests__/`); end-to-end verification still relies on `tools/sentiment-cli/`, `tools/lookup-harness/`, and device runs (`docs/debug-testing.md`).
- EAS build profiles (`eas.json`): `development` (Debug, internal), `preview` (Release, internal), `production` (store).

## Architecture

The main user flow is `app/index.tsx` driving a `idle → recording → processing → review → responseLookup → results` state machine:

1. `recording` — audio capture via `hooks/use-audio-recorder.ts`
2. `processing` — transcription (`hooks/use-transcriber.ts`) then sentiment + anonymization (`hooks/use-sentiment-analyzer.ts`), chained by `useEffect`s
3. `review` — user sees the anonymized text and emotion metadata before consenting to send it off-device (privacy checkpoint)
4. `responseLookup` — POSTs to backend via `hooks/use-spiritual-response-lookup.ts`
5. `results` — renders the response or errors

Each step is a hook with `{ result, isLoading, error, action, reset }`. If adding another pipeline step, follow the pattern: a focused hook plus a `useEffect` in `app/index.tsx` that chains to the next step.

### Privacy boundary

Only the on-device anonymized text and sentiment metadata leave the device. Request body: `{ appVariant, anonymizedText, sentiment, emotions, confidence }` — no audio, raw transcript, audio file path, recording duration, or device identifiers. `services/lookup-client.ts` is the only outbound network call; anything new that hits the network goes through there or it breaks the privacy posture.

### Env config (two layers)

`app.config.js` reads `EXPO_PUBLIC_LOOKUP_API_URL`, `EXPO_PUBLIC_LOOKUP_CLIENT_SECRET`, `EXPO_PUBLIC_APP_VARIANT` and writes them into `app.json extra`. At runtime, `services/lookup-client.ts` checks `Constants.expoConfig.extra` first, then falls back to the bundle-time `process.env` values (handles cases where `app.json` extras still hold literal placeholder strings). A build without `lookupApiUrl` throws `MissingLookupApiUrlError` before any network call — the emergency-rollback path to on-device-only flow.

### Hosted backend (`server/`)

FastAPI deployed to Fly.io. `POST /lookup` is the only endpoint that does work. The backend scans for crisis keywords (informational `crisisFlag`, no prompt branching), dispatches by `appVariant` to a registered adapter. Christian adapter: LLM picks 1 primary + 2 alternate Bible references, server fetches canonical text from the Bible API before responding. Stoic: stub returning `not_implemented`.

Provider chain default: Gemini Flash → OpenRouter free → Groq, configurable via `LOOKUP_PROVIDER_ORDER`. Runner registry also supports Cloudflare, Together, Cerebras. Providers are one-shot with immediate 429 fallback and bounded jittered retries.

**Free chain is primary.** Home GPU is overflow-only (see `docs/superpowers/home-gpu-overflow-plan.md`).

The Mac-local harness (`tools/lookup-harness/`) is the right place to iterate prompts and provider behavior. When changing prompts or adapter logic, port to both `server/` and the harness. Treat `server/` as source of truth.

### Planned versions

1. **Christian (v1)** — implemented.
2. **Stoic (v2)** — stub; catalog not yet seeded. Governed by `docs/stoic-curation-rubric.md`.
3. **Dhammapada (v3)** — committed. Backend-owned curated catalog (423 verses), LLM picks IDs from an approved index, server returns canonical text from the catalog. Crisis-flag hard-excludes high-risk passages from the index *before* the LLM sees it (stricter than Christian). Source/rights review is a strict gate before any labeling or adapter work. See `openspec/changes/dhammapada-catalog-lookup/` for the in-flight plan; `docs/other_wisdom_sources.md` lists v4+ candidates.

Product shape: **"short, concrete passage."** Keep lookup single-turn. Do not add chat memory, thread state, accounts, feeds, or persistent history.

## Sentiment Analyzer and Anonymizer

Most complex hook, easiest to regress. `analyze()` gates on `getTextModelAvailability()`, tries two paths:

1. `generateObject()` with `SENTIMENT_SCHEMA` (`{ sentiment, emotions, confidence, anonymizedText }`)
2. On failure, `generateText()` + hand-written `extractFirstJSONObject()` brace matcher

Both paths normalize via alias maps (`SENTIMENT_ALIASES`, `EMOTION_ALIASES`) because the on-device 3B model returns loose labels (`"happy"`, `"angry"`, `"85%"`, comma-joined strings). `normalizeAnonymizedText` applies a local privacy guard — if output reuses protected terms, identifiers, or too much source wording, it falls back to a generic category-based sentence, never the original transcript.

Pure parsing (`normalizeSentiment`, `normalizeEmotions`, `normalizeConfidence`, `extractFirstJSONObject`, alias maps) lives in `hooks/sentiment-utils.ts` — RN-free so vitest can cover it. The hook owns the FM calls and orchestration; land parser changes in `sentiment-utils.ts` and extend the test suite in `hooks/__tests__/`.

When changing the prompt, schema, aliases, anonymization rules, or model package, run real examples through debug tools and device flow. Schema checks alone don't catch normalization or privacy regressions.

## Debug Tools

- **`app/debug.tsx`** — `__DEV__`-gated `/debug` route. Bypasses recording/STT; calls production `useSentimentAnalyzer()`. Shows normalized results, raw model output, strategy badge.
- **`tools/sentiment-cli/`** — Swift Package executable. `swift run sentiment-cli "text"` (or pipe stdin); `--raw` dumps unstructured output. The prompt, schema, and anonymized-text guard are duplicated from the TS hook — keep them in sync.
- **`tools/sentiment-cli/run-anonymization-samples.sh`** — 20 privacy-heavy samples through Swift CLI with `--raw`. Use to catch privacy guard regressions.
- **`tools/lookup-harness/`** — Mac-local FastAPI web app (`./start.sh`, http://localhost:8000). Shells out to Swift CLI for sentiment + anonymization, then calls a hosted provider. Iterate selection prompts here before phone implementation.

Release/TestFlight builds must not expose: `/debug`, raw transcript, sentiment JSON, guarded-anonymous debug block, provider/model name, fallback status, or retry count.

See `docs/debug-testing.md` for the full matrix, fixture workflows, and device checklist.

## Conventions

- TypeScript strict mode. Path alias `@/*` maps to repo root (`@/hooks/...`, `@/components/...`).
- Named exports everywhere — hooks and components use `export function useX()` / `export function X()`, imported as `import { X } from '@/path'`. No default exports outside of `app/` route files (which expo-router requires).
- `expo-router` file-based routing (`app/_layout.tsx` is root Stack, `app/index.tsx` is home screen).
- `typedRoutes`, `reactCompiler`, New Architecture (`newArchEnabled: true`) enabled. `newArchEnabled` is load-bearing — Foundation Models bridge requires it.
- UI uses `ThemedText`, `ThemedView`, `useThemeColor`, `constants/theme.ts`. Do not hardcode colors.
- Read `docs/on-device-ai-approach.md` and `docs/foundation-models-packages.md` before swapping the FM package or adding fallback architecture.
- `docs/testflight-launch-checklist.md` and `docs/privacy-policy.md` are load-bearing for App Store / TestFlight. Update when changing data-collection behavior or release scope.
- `docs/architecture-review-2026-05-16.md` is the most recent deepening review — read before broad refactors.

## OpenSpec Workflow

Experimental change-management workflow for larger changes. The `.opencode/` directory contains commands (`opsx-propose`, `opsx-apply`, `opsx-explore`, `opsx-archive`) and skills that drive the `openspec` CLI through structured artifacts (`proposal.md`, `design.md`, `tasks.md`). Note: `.opencode/` is **gitignored** — it's per-developer tooling, not project state. If the user invokes an OpenSpec command, follow the instructions in `.opencode/commands/*.md` and `.opencode/skills/*/SKILL.md`.
