# Recording screen: scrolling waveform + keep-awake — Design

Date: 2026-06-06
Status: Approved (pending spec review)

## Problem

Two issues on the recording screen (`christian` and `dhammapada` variants both):

1. **The level meter looks dead.** Only the two rightmost bars move with speech; the
   left bars sit pinned. Root cause: `RecordingLevelMeter` (`app/index.tsx:67`) is a
   left-to-right *volume fill* meter (`normalizedLevel * 5 - index`), so the leftmost
   bars saturate to full height the moment the user speaks above a whisper and only the
   top 1–2 bars ride the loudness. It is not, and cannot easily be, a true frequency
   spectrum: `expo-av` exposes only a single overall dB level (`status.metering`), not
   per-frequency data.

2. **The screen sleeps while the user is speaking.** The app never asks iOS to stay
   awake, so the idle timer / auto-lock fires mid-reflection.

## Constraints

- **Privacy allowlist is untouched.** No new fields enter the lookup request. Recording
  `duration` is used only locally (timer + auto-stop cap) and is never sent to the
  backend or logged. `services/__tests__/lookup-request.test.ts` is unaffected.
- **`use-audio-recorder.ts` is not unit-testable** (RN/native; vitest is pure-TS only).
  Any new logic worth testing must be extracted as a pure, no-RN helper, matching the
  existing `hooks/sentiment-utils.ts` pattern.
- **Reduce-motion is respected** elsewhere (the stop-button pulse halo is gated on
  `reduceMotionEnabled`); the new visualization must respect it too.
- **`ios/` is generated** from Expo prebuild and git-ignored. A new native dependency
  requires a rebuild (`npx expo run:ios`) to take effect; no durable edits to `ios/`.

## Feature 1 — Scrolling waveform meter

Replace the left-fill `RecordingLevelMeter` with a scrolling history of thin bars
(Voice-Memos style): each bar is a recent moment of speech, the row shifts left over
time, and every bar reflects a real sample the user spoke.

### Behavior

- Maintain a fixed-length history buffer of recent `inputLevel` samples (~24–28 entries;
  exact count tuned during implementation to fit the meter width with thin bars).
- The hook already emits a smoothed `inputLevel` ~8×/sec (every
  `STATUS_UPDATE_INTERVAL_MS = 120`ms) with attack/release smoothing already applied —
  the ideal cadence to push one sample per update. No extra smoothing or timers needed.
- On each new `inputLevel`: push onto the right, drop the oldest on the left → scroll-left.
- Per-bar height = `MIN_HEIGHT + level * HEIGHT_RANGE`, the same mapping as today but
  applied per sample. Silence → flat low line; speech → a moving hill scrolling left.
- The buffer initializes to a flat line (zeros). The component only mounts while
  `appState === 'recording'`, so each recording starts fresh with no reset logic needed.
- Stays inside the existing 30px-tall meter region; same destructive-red color; keep
  `accessibilityRole="image"` and `accessibilityLabel="Live microphone input level"`.

### Reduce-motion fallback

When `reduceMotionEnabled` is true, render a non-scrolling row whose bar heights reflect
the **current** level only (no horizontal motion) — a calm in-place level indication.
`reduceMotionEnabled` is already available in `HomeScreen` and can be passed to the meter.

### Testable extraction

Extract the buffer update as a pure helper, e.g.:

```ts
// no RN imports — unit-testable under vitest
function pushSample(history: number[], level: number, size: number): number[]
```

Returns a new array of length `size` with `level` appended and the oldest dropped (and
left-padded with zeros if shorter than `size`). Add a unit test alongside it.

## Feature 2 — Keep-awake + 90s auto-stop

### Keep-awake

- Add the `expo-keep-awake` dependency (Expo SDK package; no config plugin required).
- An effect in `HomeScreen` activates keep-awake while `appState` is one of the "working"
  states — `recording`, `processing`, `responseLookup` — and deactivates on exit:

  ```ts
  useEffect(() => {
    const working = appState === 'recording'
      || appState === 'processing'
      || appState === 'responseLookup';
    if (!working) return;
    activateKeepAwakeAsync(KEEP_AWAKE_TAG);
    return () => { deactivateKeepAwake(KEEP_AWAKE_TAG); };
  }, [appState]);
  ```

  This covers the report (sleeping while speaking) plus the brief waits where the user
  watches the processing halo.

### 90s auto-stop cap

- `duration` (seconds) is already exposed from `useAudioRecorder` and ticks each second.
- An effect: when `appState === 'recording' && duration >= MAX_RECORDING_SECONDS` (90),
  call the existing `handleStop()`. It flows into `processing` exactly like a manual stop.
  The `appState === 'recording'` guard ensures it fires once (handleStop moves state off
  `recording`).
- In the final ~10s, soften the recording hint from `Recording...` to `Wrapping up soon…`
  so the cut is not abrupt.
- `MAX_RECORDING_SECONDS` lives in `HomeScreen` (which owns `appState` and `handleStop`).

## Files touched

- `app/index.tsx` — rewrite `RecordingLevelMeter` (scrolling + reduce-motion fallback);
  add keep-awake effect, auto-stop effect, hint-near-cap logic, new constants.
- New no-RN helper module + its vitest test for `pushSample`.
- `package.json` — add `expo-keep-awake`.

## Out of scope

- True frequency-spectrum analysis (would require raw-audio FFT; not available from
  `expo-av` and counter to the privacy posture).
- Any change to the lookup request, backend, or transcription pipeline.

## Verification

- `npm run typecheck`, `npm run lint`, `npm test` (covers the new `pushSample` test).
- Manual on-device (`npx expo run:ios --device`, both variants): waveform scrolls and all
  bars move with speech; reduce-motion shows the calm in-place fallback; screen does not
  sleep while recording; recording auto-stops at 90s with the "Wrapping up soon…" hint in
  the last ~10s. A rebuild is required to pick up `expo-keep-awake`.
