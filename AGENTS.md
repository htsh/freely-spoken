# Repository Guidelines

## Project

`mic-check` is an iOS-only Expo / React Native proof of concept. It records audio, transcribes it on-device with Apple Speech, then analyzes sentiment/emotions and produces anonymized text with Apple's on-device Foundation Models LLM. There is no backend, Android support, web support target, or persistent storage.

This app cannot run in Expo Go. It depends on native modules for audio, speech recognition, and Foundation Models, so use native iOS builds.

## Commands

```bash
npm install
npx expo prebuild
npx expo run:ios --device
npm run lint
```

Notes:

- `npx expo prebuild` regenerates `ios/`, which is gitignored. Do not make durable app changes directly inside generated native projects.
- The full recording and transcription flow requires a real Apple Intelligence-capable iOS device with iOS 26+, Apple Intelligence enabled, microphone permission, and speech recognition permission.
- There is no automated test suite yet. Use `npm run lint` plus the manual debug paths in `docs/debug-testing.md`.

## Architecture

The main user flow lives in `app/index.tsx` as an `idle -> recording -> processing -> results` state machine. Hooks own the work:

- `hooks/use-audio-recorder.ts` wraps `expo-av` recording and returns a recording URI on stop.
- `hooks/use-transcriber.ts` calls `ExpoSpeechRecognitionModule.start({ audioSource: { uri }, requiresOnDeviceRecognition: true })` and receives transcript/error state through speech recognition events.
- `hooks/use-sentiment-analyzer.ts` calls Apple Foundation Models, normalizes the model output for the UI, and returns an anonymized version of the transcript.

`processing` covers both transcription and sentiment analysis. If adding another pipeline step, follow the existing pattern: a focused hook with state, action, and reset methods, plus `useEffect` transitions in `app/index.tsx`.

## Sentiment Analyzer and Anonymizer

`useSentimentAnalyzer.analyze()` gates on `getTextModelAvailability()`, then tries two model paths:

1. `generateObject()` with the JSON schema in `SENTIMENT_SCHEMA`.
2. On failure, `generateText()` with `SENTIMENT_PROMPT`, then `extractFirstJSONObject()` parses the first JSON object from free-form output.

The schema includes `{ sentiment, emotions, confidence, anonymizedText }`. `anonymizedText` is intended to preserve the emotional gist and broad concern while removing names, exact locations, organizations, dates, contact details, medical/legal/financial identifiers, and uniquely identifying events.

Both paths normalize via `normalizeSentiment`, `normalizeEmotions`, `normalizeConfidence`, and `normalizeAnonymizedText`. The alias maps are important because the local model can return loose labels such as `happy`, `angry`, percentages, or comma-joined emotion strings. The anonymized-text normalizer deliberately falls back to a generic safe sentence rather than the original transcript if the model omits the field.

When changing the prompt, schema, aliases, anonymization rules, or model package, run real examples through the debug tools and the device flow. Schema checks alone do not catch normalization or privacy regressions.

## Debug Tools

Two dev-only affordances exist for sentiment work:

- `app/debug.tsx`: a `__DEV__`-gated `/debug` route linked from the home screen. It bypasses recording and STT, calls the production `useSentimentAnalyzer()` hook, and shows normalized sentiment, anonymized text, raw model output, and strategy (`object` or `text-fallback`).
- `tools/sentiment-cli/`: a Swift Package executable that calls `FoundationModels` directly on macOS. It is useful for prompt sweeps and raw model inspection before TypeScript normalization.

The Swift CLI intentionally duplicates the prompt/schema from `hooks/use-sentiment-analyzer.ts`. Keep `tools/sentiment-cli/Sources/sentiment-cli/main.swift` in sync with the TypeScript hook when changing sentiment or anonymization behavior. The CLI does not mirror the TypeScript normalization, JSON brace-matching layer, or conservative anonymized-text fallback.

See `docs/debug-testing.md` for exact workflows and what each path proves.

## Conventions

- TypeScript strict mode is enabled.
- Path alias `@/*` maps to the repo root.
- Routing uses `expo-router` file-based routes.
- `typedRoutes`, `reactCompiler`, and the React Native New Architecture are enabled in `app.json`.
- UI should use `ThemedText`, `ThemedView`, `useThemeColor`, and `constants/theme.ts` rather than one-off colors unless matching an existing local pattern.
- Read `docs/on-device-ai-approach.md` and `docs/foundation-models-packages.md` before replacing the Foundation Models package or adding fallback architecture.
