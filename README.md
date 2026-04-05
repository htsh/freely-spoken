# mic-check

A proof-of-concept iOS app for recording speech, transcribing it on-device, and analyzing sentiment using Apple Intelligence.

## What it does

1. **Record** - Tap to record audio
2. **Transcribe** - On-device speech recognition converts audio to text (Apple Speech / SFSpeechRecognizer)
3. **Analyze** - Apple Foundation Models extract sentiment and emotions from the transcript, entirely on-device

## Tech stack

- React Native (Expo SDK 54)
- TypeScript
- `expo-av` — audio recording
- `expo-speech-recognition` — on-device transcription
- `@ratley/react-native-apple-foundation-models` — on-device sentiment extraction via Apple Intelligence

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

## Troubleshooting

| Problem | Fix |
|---|---|
| "Apple Intelligence not available" | Ensure iOS 26+ is installed and Apple Intelligence is enabled in Settings > Apple Intelligence & Siri |
| Speech recognition fails | Check that the device language includes English, and that you've granted the speech recognition permission |
| Build fails at pod install | Run `cd ios && pod install --repo-update && cd ..` then rebuild |
| Signing errors | Open `ios/miccheck.xcworkspace` in Xcode and configure your development team under Signing & Capabilities |
| No sound recorded | Make sure you allowed microphone access. Check Settings > mic-check > Microphone |

## Status

Early proof of concept. iOS only. No persistent storage, no server, no Android support.
