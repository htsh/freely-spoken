# Review Before Verse Lookup Design

## Goal

Make the privacy boundary visible and user-controlled: after recording, the app shows that audio is being transcribed and anonymized on device, then shows the exact anonymized text that will leave the device before the user requests a verse.

## User Flow

1. **Idle** - User taps record.
2. **Recording** - User speaks and stops recording.
3. **Private processing** - The app shows a calm privacy cue while it transcribes and anonymizes on device.
4. **Review before sending** - The app displays the anonymized text and a brief privacy statement: audio and raw transcript stay on device.
5. **Find My Verse** - User taps a button to send only the anonymized payload to the backend.
6. **Finding verse** - The app shows the off-device lookup step.
7. **Results** - The verse response appears.

## Interaction Copy

Primary call to action:

> Find My Verse

Rationale: It is clear, warm, and specific to the Christian v1. Future variants should use variant-specific labels such as "Find My Passage" while sharing the same internal lookup action.

Review screen privacy copy:

> This is what leaves your device.
>
> Your audio and raw transcript stay on this device. Only this anonymized summary and general emotional metadata are sent to find a verse.

## State Machine

Add a `review` state between `processing` and `responseLookup`.

- `processing` still covers transcription and sentiment/anonymization.
- When anonymization succeeds, transition to `review` instead of automatically calling lookup.
- `review` renders the anonymized text and the lookup CTA.
- Tapping the CTA builds the existing `LookupRequest`, transitions to `responseLookup`, and calls the existing lookup hook.
- Analyzer failure still transitions to `results` so errors remain visible.

## UI Direction

The processing cue should feel like a privacy pipeline, not a generic spinner. Use the existing brand colors with a compact step list:

- Transcribing on device
- Removing identifying details
- Preparing private summary

The review screen should avoid showing raw transcript by default. Raw transcript can remain in the final debug/result surface for now because the current app is still in internal testing, but the pre-lookup review must center the anonymized text.

## Verification

Run `npm run lint`. Manually exercise the flow in the dev route/device flow:

- Recording stop enters private processing.
- Successful anonymization enters review and does not hit lookup automatically.
- Tapping "Find My Verse" starts lookup.
- Lookup success reaches results.
- Lookup retry still works from results.
