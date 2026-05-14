# mic-check

A proof-of-concept iOS app for recording speech, transcribing it on-device, analyzing sentiment, and producing anonymized text using Apple Intelligence.

## What it does

1. **Record** - Tap to record audio
2. **Transcribe** - On-device speech recognition converts audio to text (Apple Speech / SFSpeechRecognizer)
3. **Analyze** - Apple Foundation Models extract sentiment, emotions, confidence, and an anonymized version of the transcript, entirely on-device

## Tech stack

- React Native (Expo SDK 54)
- TypeScript
- `expo-av` — audio recording
- `expo-speech-recognition` — on-device transcription
- `@ratley/react-native-apple-foundation-models` — on-device sentiment extraction and anonymization via Apple Intelligence

## Requirements

- **macOS** with Xcode installed
- **iOS 26+** on your test device (Apple Intelligence requires the iOS 26 beta)
- **Apple Intelligence-capable hardware**: iPhone 15 Pro, iPhone 16 series, or M1+ iPad/Mac
- Apple Intelligence must be **enabled** in Settings > Apple Intelligence & Siri
- An [Apple Developer account](https://developer.apple.com/) to deploy to a physical device

## Getting started

### 1. Install dependencies

```bash
npm install
```

### 2. Generate native project

This app uses native modules (microphone, speech recognition, Foundation Models) so it cannot run in Expo Go. You need a native build.

```bash
npx expo prebuild
```

This generates the `ios/` directory with the Xcode project.

### 3. Run on device

```bash
npx expo run:ios --device
```

This will:

- Build the native iOS project
- Prompt you to select a connected device
- Install and launch the app

> **Note:** If this is your first time deploying to a physical device, Xcode may ask you to configure signing. Open `ios/miccheck.xcworkspace` in Xcode, go to Signing & Capabilities, and select your development team.

### 4. Grant permissions

On first launch, the app will request:

- **Microphone access** — required for recording
- **Speech recognition** — required for transcription

Allow both.

## Debugging and testing

There is no automated test suite yet. Start with:

```bash
npm run lint
```

For sentiment and anonymization iteration without recording audio, use the dev-only `Debug -> sentiment + privacy` link on the home screen. It opens `/debug`, runs the production sentiment hook, and shows normalized results, anonymized text, and raw model output.

For faster prompt checks on macOS, use the Swift CLI:

```bash
cd tools/sentiment-cli
swift run sentiment-cli --raw "My name is Maya Patel, I work at Northstar Clinic in Denver, and I feel scared."
```

For iterating on verse-selection prompts with sample inputs in a web UI, use the lookup harness:

```bash
cd tools/lookup-harness
./start.sh
```

See [tools/lookup-harness/README.md](tools/lookup-harness/README.md) for setup details.

See [docs/debug-testing.md](docs/debug-testing.md) for the full test matrix, fixture workflow, and end-to-end device checklist.

## Troubleshooting

| Problem                            | Fix                                                                                                        |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| "Apple Intelligence not available" | Ensure iOS 26+ is installed and Apple Intelligence is enabled in Settings > Apple Intelligence & Siri      |
| Speech recognition fails           | Check that the device language includes English, and that you've granted the speech recognition permission |
| Build fails at pod install         | Run `cd ios && pod install --repo-update && cd ..` then rebuild                                            |
| Signing errors                     | Open `ios/miccheck.xcworkspace` in Xcode and configure your development team under Signing & Capabilities  |
| No sound recorded                  | Make sure you allowed microphone access. Check Settings > mic-check > Microphone                           |

## Status

Early proof of concept. iOS only. No persistent storage, no server, no Android support.

## Next phase (planned)

The next step is a one-shot "speak your problem" flow that keeps privacy-first behavior from the current app. Product direction is now two related versions: Christian and Zen.

1. Record + on-device transcription
2. On-device sentiment + anonymization
3. Send only the anonymized text to a free hosted LLM for reference selection
4. Fetch canonical source text from the active version's trusted source
5. Return one focused response for the active version

### Planned versions

- **Christian version** — scripture-oriented response. The LLM selects a verse reference, then the app fetches verse text from a Bible API.
- **Zen version** — Zen-oriented response. The LLM selects a koan/reference, then the app fetches koan text from a koan collection.

Shared infrastructure should stay separate from version-specific prompts, response copy, content sources, and visual direction.

The app may read the fetched verse or koan aloud to the user. If added, read-aloud should use fetched canonical text, not provider-generated text.

### Planned hosted inference strategy

- Start with Gemini Flash (free tier) as primary provider.
- If provider returns `429` (rate-limited), fall back to OpenRouter free models.
- Add bounded retries with jitter for transient failures (`429`, `5xx`, timeouts).
- Keep this as single-turn inference, not a chat session.

### Privacy posture for hosted calls

- Never send raw transcript audio to cloud providers.
- Never send raw transcript text to cloud providers.
- Send only anonymized text generated by the on-device anonymization guard.

### Future scope

- Keep core UX as a tight one-time interaction.
- Current scope is exactly two versions: Christian and Zen.
- Do not broaden to additional traditions unless a future plan explicitly changes that.
