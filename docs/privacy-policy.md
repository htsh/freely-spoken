# Privacy Policy for Freely Spoken

**Last updated:** May 30, 2026

Freely Spoken is a privacy-first iOS app for spoken reflection. The Christian build is released as **Freely Spoken**. The Buddhist/Dhammapada build is released as **Idle Ashes**. This policy describes the shared privacy behavior of both variants.

## Summary

The app is designed so the most sensitive data stays on your device:

- Audio recordings are processed on-device and are not uploaded.
- Raw transcripts are processed on-device and are not uploaded.
- Apple Foundation Models create an anonymized summary on-device.
- You review the anonymized summary before it is sent to the backend.
- The backend receives only the anonymized summary, sentiment metadata, confidence score, and app variant.

## What the app processes on your device

### Audio recordings

When you tap the record button, the app captures audio using your device's microphone. The audio is used to produce a transcript on your device. The app does not upload, persist, or intentionally retain the audio recording.

### Speech transcription

Your recording is transcribed on-device using Apple's speech recognition frameworks. The raw transcript is used locally for sentiment analysis and anonymization. The raw transcript is not sent to the backend.

### Sentiment and anonymization

The app uses Apple Foundation Models on-device to:

- identify broad sentiment and emotional tone
- produce a short anonymized summary
- remove names, places, dates, contact details, organizations, and other identifying details where possible

The app also applies local guardrails to reject anonymized summaries that appear to preserve protected terms, sensitive patterns, or too much wording from the original transcript.

## What leaves your device

After the review step, the app sends this shape to the backend:

```json
{
  "appVariant": "christian",
  "anonymizedText": "the person feels overwhelmed by a difficult situation",
  "sentiment": "negative",
  "emotions": ["anxiety", "frustration"],
  "confidence": 0.65
}
```

The app does not send:

- audio recordings
- raw transcripts
- names, email addresses, Apple IDs, or account identifiers
- device identifiers
- location
- audio file paths
- recording duration
- persistent session or chat history

## How the backend uses the data

The backend uses the anonymized summary and sentiment metadata to select a relevant canonical passage. The backend may send the anonymized summary and related sentiment metadata to configured LLM providers for reference selection.

The LLM is used for selection, not as the source of canonical passage text:

- In the Christian variant, the model selects Bible references, and the server fetches canonical Bible text from a Bible API.
- In the Dhammapada variant, the model selects passage IDs from a curated backend catalog, and the server returns canonical text from that catalog.

The backend is designed not to log the anonymized text body. It may log operational metadata such as request ID, app variant, sentiment label, emotion labels, confidence score, anonymized text length, provider name, outcome, fallback status, retry count, and latency.

## Third-party services

### Apple

Audio transcription and on-device language model processing use Apple operating system frameworks, including Speech Recognition and Apple Foundation Models. These processes run on supported Apple devices and are governed by [Apple's Privacy Policy](https://www.apple.com/legal/privacy/).

### LLM providers

The backend may use configured LLM providers such as Gemini, OpenRouter, Groq, or other compatible providers. These providers receive only the anonymized summary and related sentiment metadata needed for reference selection. They do not receive audio or raw transcripts from the app.

### Canonical text providers

For the Christian variant, the backend may fetch Bible passage text from a Bible API using a book/chapter/verse reference. This lookup does not include the user's audio, raw transcript, or anonymized summary.

For the Dhammapada variant, canonical passage text is loaded from the backend catalog and does not require a third-party text lookup.

### Hosting and infrastructure

The backend may run on cloud hosting infrastructure. Hosting providers may process ordinary server and network metadata required to operate the service.

## Data retention

The app does not create accounts, store recordings, store transcripts, or maintain persistent history.

The backend code is designed not to store request bodies or anonymized summaries in an application database. Operational logs may be retained by the deployment environment according to its configuration and provider defaults.

## How we use the data

The anonymized summary and sentiment metadata are used only to return a relevant passage response and operate the service.

We do not:

- sell user data
- use user data for advertising profiles
- train models on audio or raw transcripts
- build user histories or accounts

## Your choices

You can stop before the review step and avoid sending anything to the backend. If you do send a request, only the reviewed anonymized summary and sentiment metadata are transmitted.

You can also deny microphone or speech recognition permissions in iOS Settings, though the app cannot perform the recording flow without them.

## Children

This app is not intended for children under 13. We do not knowingly collect personal information from children.

## Changes to this policy

If this policy changes materially, the updated policy will include a new "Last updated" date.

## Contact

For privacy questions or concerns, contact:

Hitesh Aidasani

hitesh@gmail.com
