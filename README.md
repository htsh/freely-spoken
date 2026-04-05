# mic-check

A proof-of-concept iOS app for recording speech, transcribing it, and analyzing sentiment.

## What it does

1. **Record** - Speaker taps a button to record audio
2. **Transcribe** - Audio is transcribed to text (via Whisper or similar)
3. **Analyze** - iOS Apple Intelligence APIs extract sentiment and other insights from the transcript

## Tech stack

- React Native (Expo)
- TypeScript
- expo-av (audio recording)
- Apple Intelligence / NLKit (on-device sentiment analysis)

## Getting started

```bash
npm install
npx expo start
```

## Status

Early proof of concept. iOS only for now.
