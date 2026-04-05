# mic-check PoC Design

## Goal

Prove that we can record audio on iOS, transcribe it on-device, and extract sentiment/emotions using Apple Foundation Models — all without leaving the device.

## App flow

Single screen with three states:

1. **Idle** — centered record button, "Tap to record" label
2. **Recording** — stop button, elapsed timer
3. **Results** — loading spinner while transcribing/extracting, then:
   - Transcript text
   - Sentiment (positive / negative / neutral)
   - Detected emotions
   - "Record again" button to reset

## Tech choices

| Concern | Solution |
|---|---|
| Audio recording | `expo-av` — captures to file |
| Transcription | `expo-speech-recognition` — on-device, feed recorded audio |
| Sentiment extraction | `@ratley/react-native-apple-foundation-models` — `generateObject` with JSON schema |
| Navigation | Single screen, no tabs |
| Styling | Minimal, no animations or polish |

## Extraction schema

```json
{
  "sentiment": "positive | negative | neutral",
  "emotions": ["joy", "sadness", "anger", "fear", "surprise", "disgust", "hope", "anxiety", "peace", "love", "gratitude"],
  "confidence": 0.85
}
```

Closed set of emotion labels. Low temperature (0.2) for consistency.

## Out of scope

- Persistent storage
- Server-side fallback
- Android support
- Polished UI / animations
- Whisper integration (future upgrade path)
