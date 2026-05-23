# Lookup Wait Cue Design

## Goal

Make the off-device response lookup feel as transparent and intentional as the earlier private-processing step. Replace the plain "Finding a response..." label with a calm, branded progress cue that explains what is happening without exposing release-only debug details.

## User Flow

1. User reviews the anonymized summary.
2. User taps the variant-specific lookup CTA.
3. The app enters `responseLookup`.
4. The app shows a lookup cue with a short step list while the existing one-shot `/lookup` request is in flight.
5. The app transitions to results when lookup succeeds or fails.

## UI Direction

Reuse the visual language from `PrivateProcessingCue`: centered halo, subtitle, trust line, and compact step list.

Variant title:

- Christian: `Finding a verse...`
- Stoic: `Finding a passage...`

Trust line:

> Only the anonymized summary and general emotional metadata are being used.

Steps:

- `Private summary ready` - done
- `Selecting a response` - active
- `Fetching canonical text` - pending

## Release Privacy Boundary

Do not show provider names, model names, fallback status, retry counts, or backend routing details in the release UI. The mobile app currently makes a single `POST /lookup` request and only receives final response metadata, so real-time provider status would be inferred rather than observed.

Provider/model metadata can continue to appear only in existing `__DEV__` diagnostics after results.

## Implementation Changes

- Add a small `LookupProgressCue` component in `app/index.tsx`.
- Replace the current `responseLookup` centered text with that component.
- Reuse existing processing styles where practical so this remains a narrow UI change.
- Keep backend and lookup-client behavior unchanged.

## Verification

- Run `npm run lint`.
- Manually verify that `responseLookup` shows the new progress cue.
- Verify Christian and Stoic variants render the correct title noun.
- Verify release UI does not expose provider/model/fallback/retry details during the wait.
