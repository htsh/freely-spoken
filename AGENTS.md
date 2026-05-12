# Repository Guidelines

Note: `CLAUDE.md` also exists as a parallel instruction file for Claude Code. This file is the primary reference for OpenCode sessions.

## Project

`mic-check` is an iOS-only Expo / React Native proof of concept. It records audio, transcribes it on-device with Apple Speech, then analyzes sentiment/emotions and produces anonymized text with Apple's on-device Foundation Models LLM. There is no backend, Android support, web support target, or persistent storage.

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

The main user flow lives in `app/index.tsx` as an `idle → recording → processing → results` state machine. Two `useEffect`s chain the pipeline. Hooks own the work:

- `hooks/use-audio-recorder.ts` — wraps `expo-av` `Audio.Recording`, returns `{ duration, startRecording, stopRecording }`. Tears down on unmount.
- `hooks/use-transcriber.ts` — calls `ExpoSpeechRecognitionModule.start({ audioSource: { uri }, requiresOnDeviceRecognition: true })`, receives results via `useSpeechRecognitionEvent`. Returns `{ transcript, isTranscribing, error, transcribe, reset }`.
- `hooks/use-sentiment-analyzer.ts` — calls Apple Foundation Models, normalizes output, returns anonymized transcript. Returns `{ result, raw, isAnalyzing, error, analyze, reset }`.

The `processing` state covers both transcription and sentiment analysis. If adding another pipeline step, follow the pattern: a focused hook with result/isLoading/error/action/reset, plus a `useEffect` in `app/index.tsx` that chains to the next step.

### Planned pipeline extension (hosted verse retrieval)

The next planned step is a hosted LLM verse lookup after anonymization. Target flow:

`idle -> recording -> processing (transcribe + anonymize) -> verseLookup -> results`

Implementation guidance for upcoming work:

- Add a dedicated hook (for example `hooks/use-verse-lookup.ts`) with `{ result, isLoading, error, lookup, reset }`.
- Only pass anonymized text into hosted inference. Do not send raw transcript.
- Keep lookup single-turn (no chat memory, no thread state).
- Provider order should support fallback:
  1. Primary: Gemini Flash free tier
  2. Fallback: OpenRouter free model(s)
- On `429`, immediately attempt fallback provider.
- Add bounded retries with jitter for transient errors (`429`, `5xx`, timeout).
- Return one verse plus structured metadata (reference, text, provider, model, retry count, fallback-used flag) so UI/debug can show strategy.

This is intentionally a tight loop product direction: "speak once, receive one relevant verse".

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
- Future optional scope may include additional religious text corpora (for example Hindu, Muslim, Buddhist), but the interaction model should remain one-shot rather than chat.
