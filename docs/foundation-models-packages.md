# Apple Foundation Models: React Native Package Comparison

All four packages bridge Apple's on-device ~3B LLM (iOS 26+) into React Native. All require New Architecture enabled and Apple Intelligence-capable hardware.

---

## 1. @react-native-ai/apple

**What it is:** A Vercel AI SDK provider. Plugs into the `ai` package so you get the same `generateText` / `generateObject` / `streamText` API you'd use with OpenAI or Anthropic.

- **Pros:** Consistent API if you're already using Vercel AI SDK. Good ecosystem alignment. Streaming support.
- **Cons:** Pulls in the full `ai` SDK as a dependency. Requires React Native 0.80+ or Expo Canary. Heavier dependency tree for a PoC.
- **Best for:** Apps already using the Vercel AI SDK, or planning to swap between on-device and cloud models.

**Links:** Part of the `ai` package ecosystem (Vercel)

---

## 2. @ratley/react-native-apple-foundation-models

**What it is:** Lightweight standalone bridge. Exposes `generateText` and `generateObject` directly with JSON schema support.

- **Pros:** Minimal dependencies. Simple API. Structured output with schema validation built in. Expo compatible via `npx expo prebuild`.
- **Cons:** Smaller community / newer. Less battle-tested. Fewer features than some alternatives.
- **Best for:** Quick integration when you just need text generation and structured output without extra framework overhead.

**Links:** npm `@ratley/react-native-apple-foundation-models`

---

## 3. react-native-apple-llm

**What it is:** Full-featured bridge with sessions, structured JSON output, streaming, and tool calling support.

- **Pros:** Most complete feature set. Session management (multi-turn conversations). Tool calling support. Streaming.
- **Cons:** More manual setup. Slightly more complex API surface.
- **Best for:** Apps that need multi-turn conversations, tool use, or fine-grained control over the model session.

**Links:** npm `react-native-apple-llm`

---

## 4. react-native-apple-intelligence

**What it is:** Nitro module that exposes React hooks (`useLanguageModel`). Hook-based API with streaming.

- **Pros:** Feels native to React. Hook-based API is clean for component-level usage. Streaming via hooks.
- **Cons:** Nitro dependency. Hook-based pattern may not fit all architectures (e.g., background processing outside components).
- **Best for:** Apps where you want to call the model directly from components with a React-idiomatic API.

**Links:** npm `react-native-apple-intelligence`

---

## Our pick for the PoC: @ratley/react-native-apple-foundation-models

**Why:** We need `generateObject` with a JSON schema and nothing else. It's the lightest option, Expo-compatible, and gets us to a working proof of concept fastest. If we outgrow it (need sessions, streaming, tool calling), we can swap to `react-native-apple-llm` later.

---

## Shared requirements (all packages)

| Requirement | Detail |
|---|---|
| iOS version | 26+ |
| Hardware | iPhone 15 Pro, iPhone 16 series, M1+ iPad/Mac |
| React Native | New Architecture enabled |
| Expo | Requires `npx expo prebuild` (no Expo Go) |
