# On-Device Theme Extraction for Prayer App

## Goal

Extract spiritual themes and emotions from prayer text **on the user's device** before sending anything to our server. The server only ever receives a sanitized list of themes — never raw prayer content. This is our core privacy guarantee.

---

## iOS Approach: Apple Foundation Models (Primary)

### What it is

Apple ships a ~3B parameter LLM on-device with iOS 26+. Developers can access it via the **Foundation Models framework**. It runs locally, works offline, costs nothing per inference, and no data leaves the device.

### React Native / Expo integration

There are several community packages that bridge this into React Native. Recommended options (evaluate which fits best with our Expo setup):

- **`@react-native-ai/apple`** — Vercel AI SDK provider. If we're already using the AI SDK elsewhere, this gives us consistent `generateText` / `generateObject` patterns. Requires React Native 0.80+ or Expo Canary, New Architecture enabled, iOS 26+.
- **`@ratley/react-native-apple-foundation-models`** — Lighter-weight, exposes `generateText` and `generateObject` directly with JSON schema support. Expo compatible via `npx expo prebuild`.
- **`react-native-apple-llm`** — Supports sessions, structured JSON output, streaming, and tool calling. Slightly more manual but full-featured.
- **`react-native-apple-intelligence`** — Nitro module with React hooks (`useLanguageModel`). Clean hook-based API with streaming.

All of these require:
- iOS 26+
- Apple Intelligence-capable hardware (iPhone 15 Pro, iPhone 16 series, M1+ iPad/Mac)
- New Architecture enabled in React Native

### How to use it

The key feature we need is **structured output / guided generation**. We give the model a prayer and a JSON schema, and it returns themes in a predictable format.

Pseudocode using `@ratley/react-native-apple-foundation-models`:

```typescript
import { generateObject } from "apple-foundation-models";

const PRAYER_THEMES = [
  "healing", "grief", "gratitude", "forgiveness", "family",
  "marriage", "finances", "guidance", "fear", "hope", "faith",
  "repentance", "protection", "justice", "patience", "peace",
  "loneliness", "addiction", "work", "praise", "surrender",
  "trust", "provision", "wisdom", "comfort", "salvation"
];

async function extractThemes(prayerText: string) {
  const { object } = await generateObject<{
    themes: string[];
    emotions: string[];
  }>({
    prompt: prayerText,
    instructions: `You are a prayer theme classifier. Given a prayer, identify which themes and emotions are present. 
Select themes ONLY from this list: ${PRAYER_THEMES.join(", ")}.
For emotions, use simple labels like: hope, fear, sadness, joy, anger, anxiety, peace, love, desperation, gratitude.
Do NOT repeat or paraphrase any of the prayer content.`,
    schema: {
      type: "object",
      required: ["themes", "emotions"],
      properties: {
        themes: {
          type: "array",
          items: { type: "string" }
        },
        emotions: {
          type: "array",
          items: { type: "string" }
        }
      }
    },
    temperature: 0.2,
  });

  return object; 
  // e.g. { themes: ["healing", "family", "faith"], emotions: ["fear", "hope"] }
}
```

### Availability check

Always check if the device supports Apple Intelligence before attempting to use the model. Fall back gracefully.

```typescript
import { isFoundationModelsEnabled } from "react-native-apple-llm";
// or equivalent from whichever package we choose

const status = await isFoundationModelsEnabled();
if (status === "available") {
  // Use on-device extraction
} else {
  // Fall back to server-side extraction
}
```

### Important notes

- The on-device model is good at classification, summarization, and entity extraction. It is NOT a general-knowledge chatbot — which is fine, we don't need it to be.
- Use a **closed set of theme labels** (the `PRAYER_THEMES` list above) rather than asking the model to freely generate themes. This makes 3B reliable and deterministic.
- Use low temperature (0.2) for consistency.
- Handle errors: the model can throw for guardrail violations, unsupported languages, or context window exceeded.

---

## Server-Side Fallback

For devices that don't support Apple Intelligence (iPhone 14 and earlier, or Apple Intelligence not enabled), the app sends the prayer to **our own server** over TLS. The server runs theme extraction using a local LLM (e.g., Qwen 2.5 1.5B or 3B via Ollama) and returns the same `{ themes, emotions }` JSON. The prayer text is processed in memory and not persisted.

This means the worst case is still good: prayer text goes to infrastructure we control, never to a third party.

---

## Future: Android Path

Apple Intelligence is iOS-only. For Android, we'll use one of these approaches to run a small model on-device:

- **`llama.rn`** — React Native binding for llama.cpp. Most mature option. Runs GGUF-format models on-device. Supports GPU acceleration on Snapdragon Adreno 700+. Works with both iOS and Android but we'd use it Android-only since Apple's native model is better on iOS.
- **`react-native-llm-mediapipe`** or **`expo-llm-mediapipe`** — Uses Google's MediaPipe LLM Inference. Supports Gemma 2B and similar models.
- **`react-native-ai`** (MLC engine) — Also cross-platform, integrates with Vercel AI SDK.

The tradeoff on Android: we need to **bundle or download a model file** (~350MB–1GB depending on model size and quantization). This will need a first-launch download flow with user-facing explanation of why.

Recommended model for Android: **Qwen 2.5 0.5B-Instruct** (Q4 quantized, ~350MB) for widest device compatibility, with the same closed-label classification prompt. Step up to 1.5B if testing shows the 0.5B struggles with nuance.

---

## Architecture Summary

```
┌─────────────────────────────────────────────┐
│                 USER DEVICE                  │
│                                              │
│  Prayer text                                 │
│       │                                      │
│       ▼                                      │
│  On-device model (Apple FM / llama.rn)       │
│       │                                      │
│       ▼                                      │
│  { themes: [...], emotions: [...] }          │
│       │  ← Only this leaves the device       │
└───────┼──────────────────────────────────────┘
        │ TLS
        ▼
┌─────────────────────────────────────────────┐
│              OUR SERVER                      │
│                                              │
│  Receives themes JSON                        │
│       │                                      │
│       ▼                                      │
│  Bible vector DB (pgvector / local)          │
│  + Local LLM for passage ranking/summary     │
│       │                                      │
│       ▼                                      │
│  Relevant Bible passages                     │
└───────┼──────────────────────────────────────┘
        │ TLS
        ▼
   Response to user
```

**The prayer text never leaves the device when on-device extraction is available. It never leaves our infrastructure in the fallback case.**
