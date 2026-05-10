# Debugging and Testing

This project does not have an automated test suite yet. Use the paths below depending on what you need to prove.

## Quick Matrix

| Path | Command / entry point | Proves | Does not prove |
|---|---|---|---|
| Static check | `npm run lint` | TypeScript/React lint sanity | Runtime native module behavior |
| Sentiment debug screen | Home screen -> `Debug -> sentiment` in a dev build | Production React hook, availability gate, object/fallback strategy, normalization | Recording, file URIs, Apple Speech transcription |
| Swift sentiment CLI | `cd tools/sentiment-cli && swift run sentiment-cli "text"` | Foundation Models prompt/schema behavior without rebuilding the app | TypeScript normalization, React state, UI |
| Full device flow | `npx expo run:ios --device` | Recording -> on-device STT -> sentiment -> UI result | Automated regression coverage |

## Baseline Checks

Run lint before and after behavior changes:

```bash
npm run lint
```

If dependencies or `app.json` native plugin settings changed, regenerate native projects:

```bash
npx expo prebuild
```

Do not edit generated `ios/` files as the durable source of truth. Put persistent native configuration in `app.json` plugins or app source code.

## Test Sentiment Without Recording

Use the debug route when you want to test the same React hook used by the app without recording audio.

1. Start a dev native build:

   ```bash
   npx expo run:ios --device
   ```

   For sentiment-only checks, an iOS 26 simulator on Apple Silicon can be useful if Apple Intelligence / Foundation Models reports available. If the debug screen shows an availability error, use a physical Apple Intelligence-capable device.

2. On the home screen, tap `Debug -> sentiment`.

3. Paste a transcript or tap a fixture.

4. Tap `Analyze`.

5. Check both sections:

   - `Normalized`: the values the app will render to users.
   - `Raw model output`: the pre-normalization object/text and the strategy badge.

The strategy badge matters:

- `object`: `generateObject()` succeeded with the schema.
- `text-fallback`: `generateObject()` failed, so the hook used `generateText()` and parsed JSON out of text output.

When editing `SENTIMENT_PROMPT`, `SENTIMENT_SCHEMA`, `SENTIMENT_ALIASES`, or `EMOTION_ALIASES`, include examples that cover positive, negative, neutral, mixed, ambiguous, and multi-emotion transcripts.

## Test Raw Foundation Models Output on macOS

Use the Swift CLI when you want fast prompt iteration or bulk sweeps without rebuilding React Native.

Requirements:

- macOS 26 on Apple Silicon.
- Apple Intelligence enabled in System Settings.
- Swift 6 / Xcode 26 toolchain.

Run from `tools/sentiment-cli/`:

```bash
swift run sentiment-cli "I'm feeling pretty good today, all things considered."
```

Use stdin for scripts:

```bash
echo "I keep waking up at 3am with my chest tight." | swift run sentiment-cli
```

Add `--raw` to also see the unstructured model response that resembles the TypeScript fallback path:

```bash
swift run sentiment-cli --raw "Whatever. The meeting happened. It was fine."
```

For a JSONL fixture file with one `{"text": "..."}` object per line:

```bash
jq -r '.text' fixtures.jsonl | while IFS= read -r line; do
  echo "=== $line ==="
  echo "$line" | swift run sentiment-cli --raw
done
```

Important: the CLI does not run TypeScript normalization. If the CLI returns `happy`, `angry`, `85%`, or prose around JSON, confirm the app behavior in `/debug` before deciding whether production behavior is broken.

## Test the Full Device Flow

Use this path before considering recording, speech recognition, or end-to-end UX changes complete.

1. Confirm the device is eligible:

   - iOS 26+.
   - Apple Intelligence-capable hardware.
   - Apple Intelligence enabled in Settings.
   - Microphone and Speech Recognition permissions allowed for `mic-check`.

2. Build and launch:

   ```bash
   npx expo run:ios --device
   ```

3. Record short samples:

   - Clear positive: "I am relieved and grateful that everything worked out."
   - Clear negative: "I am frustrated and scared this keeps happening."
   - Neutral: "The meeting started at nine and ended at ten."
   - Mixed: "I love them, but I am angry about what happened."

4. Verify:

   - The app leaves `recording` after stop.
   - A transcript appears, or a clear transcription error appears.
   - Sentiment and emotions appear for non-empty transcripts.
   - `Record Again` resets transcript, sentiment, and errors.

## Prompt / Schema Change Checklist

When changing sentiment behavior:

1. Update `hooks/use-sentiment-analyzer.ts`.
2. Mirror prompt/schema changes in `tools/sentiment-cli/Sources/sentiment-cli/main.swift`.
3. Run CLI examples with and without `--raw`.
4. Run the same examples through `/debug` to verify normalized production behavior.
5. Run at least one full device recording to catch STT and pipeline regressions.
6. Run `npm run lint`.

## Common Failures

| Symptom | Likely cause | What to check |
|---|---|---|
| `Apple Intelligence not available` | Device/simulator does not expose Foundation Models | OS version, Apple Intelligence setting, hardware eligibility |
| Debug route works, full flow fails | Recording or STT path problem | Microphone permission, Speech Recognition permission, device language |
| CLI looks wrong, debug route looks right | Normalization cleaned up loose model output | Alias maps and `normalizeConfidence()` |
| Debug route shows `text-fallback` often | `generateObject()` is failing schema generation | Prompt/schema compatibility and raw output |
| Build fails after dependency/plugin changes | Native project or pods stale | Rerun `npx expo prebuild`; if needed run `pod install` inside generated `ios/` |
