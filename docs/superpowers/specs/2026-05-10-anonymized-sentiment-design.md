# Anonymized Sentiment Design

## Goal

Add an on-device anonymization output to the existing sentiment workflow so the app can keep the emotional gist of a transcript while removing specifics that should not leave the device.

## Scope

This first version only produces and displays anonymized text. It does not call an external advice service, persist transcripts, or add sharing/network behavior.

## Approach

Extend the existing Foundation Models sentiment request instead of adding a second model call. The hook already gates on Apple Intelligence availability, handles structured generation, and has a text fallback path. Returning anonymized text in the same structured result keeps the flow simple and lets the debug screen compare original input, normalized sentiment, anonymized text, and raw model output in one place.

## Model Contract

The structured model result should contain:

- `sentiment`: one of `positive`, `negative`, or `neutral`.
- `emotions`: emotion labels from the existing allowed list.
- `confidence`: confidence from `0` to `1`, with existing normalization still accepting `0` to `100`.
- `anonymizedText`: a privacy-preserving rewrite that keeps the concern and emotional gist while removing identifying specifics.

The prompt should tell the model to remove or generalize names, exact locations, organizations, dates, ages, contact details, account numbers, medical/legal/financial identifiers, and uniquely identifying events. The anonymized text should not invent new facts or advice.

## App Flow

`useSentimentAnalyzer()` returns `result.anonymizedText` alongside the existing normalized sentiment fields. `app/index.tsx` shows an `Anonymous version` section on the results screen after sentiment/emotions. This confirms what would be safe to send to a future advice service.

## Debug Flow

`app/debug.tsx` shows `anonymizedText` in the normalized output block and updates fixture examples to include identifying details. Raw model output remains visible so prompt/schema failures are easy to inspect.

## Swift CLI

`tools/sentiment-cli` mirrors the TypeScript prompt and schema with an `anonymizedText` field. The CLI remains intentionally pre-normalization; it helps inspect what the model emits before the app cleans up sentiment labels and confidence.

## Testing

Use these checks:

- `npm run lint`.
- `/debug` examples covering names, exact locations, organizations, dates, ages, medical details, and mixed emotions.
- `swift run sentiment-cli --raw "<text>"` from `tools/sentiment-cli`.
- One full device recording to confirm the transcript-to-anonymized-output path.

Success means the anonymous version keeps the broad situation and emotion but removes specifics that could identify the speaker or other people.
