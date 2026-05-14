# Repository Guidelines

Note: `CLAUDE.md` also exists as a parallel instruction file for Claude Code. This file is the primary reference for OpenCode sessions.

## Project

`mic-check` is an iOS-only Expo / React Native app. It records audio, transcribes it on-device with Apple Speech, analyzes sentiment/emotions and produces anonymized text with Apple's on-device Foundation Models LLM, then calls a hosted FastAPI backend (`server/`) with just the anonymized text + sentiment metadata to receive a canonical response (a Bible verse for the Christian variant). No Android, no web target, no persistent storage, no chat or session memory.

This app **cannot run in Expo Go**. It depends on native modules for audio, speech recognition, and Foundation Models, so use native iOS builds. Apple Intelligence requires real hardware (iPhone 15 Pro/16 series, M1+ iPad/Mac), iOS 26+, and Apple Intelligence enabled in Settings. Simulators won't work for the full recording+transcription flow.

## Commands

```bash
npm install
npx expo prebuild           # regenerates ios/ (gitignored) — required after dependency or app.json changes
npx expo run:ios --device   # build native project, install on device, launch
npm run lint                # eslint via expo config (expo lint)
```

- `ios/` and `android/` are gitignored. Do not make durable app changes inside generated native projects.
- There is no automated test suite. Use `npm run lint` plus the manual debug paths in `docs/debug-testing.md`.

## Architecture

The main user flow lives in `app/index.tsx` as an `idle → recording → processing → responseLookup → results` state machine. Three `useEffect`s chain the pipeline. Hooks own the work:

- `hooks/use-audio-recorder.ts` — wraps `expo-av` `Audio.Recording`, returns `{ duration, startRecording, stopRecording }`. Tears down on unmount.
- `hooks/use-transcriber.ts` — calls `ExpoSpeechRecognitionModule.start({ audioSource: { uri }, requiresOnDeviceRecognition: true })`, receives results via `useSpeechRecognitionEvent`. Returns `{ transcript, isTranscribing, error, transcribe, reset }`.
- `hooks/use-sentiment-analyzer.ts` — calls Apple Foundation Models, normalizes output, returns anonymized transcript. Returns `{ result, raw, isAnalyzing, error, analyze, reset }`.
- `hooks/use-spiritual-response-lookup.ts` — POSTs the anonymized payload to the hosted backend via `services/lookup-client.ts` and returns `{ result, isLoading, error, lookup, reset }`. One shot per call; the backend owns provider fallback and retries.

The `processing` state covers transcription + sentiment; `responseLookup` is the off-device step. If adding another pipeline step, follow the pattern: a focused hook with result/isLoading/error/action/reset, plus a `useEffect` in `app/index.tsx` that chains to the next step.

### Privacy boundary

Only the on-device anonymized text and sentiment metadata leave the device. The request body is exactly `{ appVariant, anonymizedText, sentiment, emotions, confidence }` — no audio, no raw transcript, no audio file path, no recording duration, no device identifiers. `services/lookup-client.ts` is the only outbound network call in the app; anything that wants to hit the network goes through there or it breaks the privacy posture.

### Hosted backend (`server/`)

FastAPI service deployed to Fly.io. `POST /lookup` is the only endpoint that does work. The backend scans the anonymized text for crisis keywords (informational `crisisFlag` only — no LLM prompt branching), then dispatches by `appVariant` to a registered adapter:

- Christian (`server/app/lookup/christian.py`) — LLM picks 1 primary + 2 alternate Bible references, server fetches canonical text from the configured Bible API (default `bible-api.com`, World English Bible) before responding. LLM output is never returned as scripture text. Individual fetch failures become per-reference `textError`; the call only fails when every fetch fails.
- Stoic — stub adapter returning `{ status: "not_implemented", appVariant: "stoic" }` until the catalog is seeded.

Provider chain (Gemini Flash → OpenRouter free → Groq, configurable via `LOOKUP_PROVIDER_ORDER`) lives in `server/app/llm_runner.py`. Providers are one-shot; the runner does immediate fallback on 429 and bounded jittered retries on transient errors. Device config in `app.json` `extra`: `lookupApiUrl`, `lookupClientSecret`, `appVariant`. A build without `lookupApiUrl` set is the emergency-rollback path back to the on-device-only flow.

The Mac-local harness (`tools/lookup-harness/`) is the right place to iterate prompts and provider behavior — faster cycle than redeploying. When changing prompts or adapter logic, port the change to both `server/` and the harness (or document the divergence intentionally). Treat `server/` as the source of truth for production behavior.

## Sentiment Analyzer and Anonymizer

This is the most complex hook and the easiest to regress. `analyze()` gates on `getTextModelAvailability()`, then tries two paths:

1. `generateObject()` with `SENTIMENT_SCHEMA` (JSON schema for `{ sentiment, emotions, confidence, anonymizedText }`).
2. On failure, `generateText()` with `SENTIMENT_PROMPT`, then `extractFirstJSONObject()` parses the first JSON object from free-form output.

Both paths normalize via `normalizeSentiment`, `normalizeEmotions`, `normalizeConfidence`, and `normalizeAnonymizedText`. The alias maps (`SENTIMENT_ALIASES`, `EMOTION_ALIASES`) are critical because the on-device 3B model returns loose labels (`"happy"`, `"angry"`, `"85%"`, comma-joined strings). `normalizeAnonymizedText` applies a local privacy guard: if the model output reuses protected terms, identifiers, or too much source wording, it falls back to a generic category-based safe sentence — never the original transcript.

When changing the prompt, schema, aliases, anonymization rules, or model package, run real examples through both debug tools and the device flow. Schema checks alone do not catch normalization or privacy regressions.

## Debug Tools

- **`app/debug.tsx`** — `__DEV__`-gated `/debug` route. Bypasses recording and STT; calls the production `useSentimentAnalyzer()` hook. Shows normalized sentiment/anonymized text, raw model output, and the strategy badge (`object` or `text-fallback`).
- **`tools/sentiment-cli/`** — Swift Package executable that calls Foundation Models directly on macOS. `swift run sentiment-cli "text"` (or pipe stdin); `--raw` also dumps unstructured `generateText` output. The prompt, schema, and anonymized-text guard are duplicated from the TypeScript hook — keep them in sync.
- **`tools/sentiment-cli/run-anonymization-samples.sh`** — runs 20 privacy-heavy samples through the Swift CLI with `--raw`. Use this to catch privacy guard regressions after changing anonymization rules.

See `docs/debug-testing.md` for the full test matrix, fixture workflows, and end-to-end device checklist.

## Conventions

- TypeScript strict mode is enabled.
- Path alias `@/*` maps to the repo root.
- Routing uses `expo-router` file-based routes (`app/_layout.tsx` is the root Stack, `app/index.tsx` is the home screen).
- `typedRoutes`, `reactCompiler`, and the React Native New Architecture (`newArchEnabled: true`) are enabled in `app.json`.
- UI should use `ThemedText`, `ThemedView`, `useThemeColor`, and `constants/theme.ts` rather than one-off colors.
- Read `docs/on-device-ai-approach.md` and `docs/foundation-models-packages.md` before replacing the Foundation Models package or adding fallback architecture.
- Current product scope is Christian (v1, implemented) and Stoic (v2, stub in the variant registry; catalog not yet seeded). A third version slot is open and intentionally undecided. Do not broaden to additional traditions unless a future plan explicitly changes that. The interaction model is one-shot, not chat.
