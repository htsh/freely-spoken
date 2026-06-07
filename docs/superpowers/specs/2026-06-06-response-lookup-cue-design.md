# Animated verse-lookup loader (`ResponseLookupCue`) — Design

Date: 2026-06-06
Status: Approved

## Problem

The `responseLookup` app state — shown while the anonymized summary is sent to the
backend provider chain and a passage is selected — currently renders a single bare line
(`app/index.tsx:393`):

```tsx
{appState === 'responseLookup' && (
  <View style={styles.center}>
    <ThemedText>Finding a response...</ThemedText>
  </View>
)}
```

The provider fallback chain can take a few seconds, so this static text feels dead. We
want an interactive, polished loading state that reads as a continuation of the existing
on-device processing screen.

## Constraints

- **Purely presentational.** No change to the lookup request, the provider chain, or any
  network field. The privacy allowlist is untouched.
- **Reduce-motion respected**, consistent with the existing recording-pulse gating
  (`app/index.tsx:275`) — animation must not run when `reduceMotionEnabled` is true.
- **Reuse the established visual language.** The `processing` state already has a polished
  `PrivateProcessingCue` (halo ring + core + title). Match it rather than inventing a new
  motif.
- **Pure logic is extracted and unit-tested**, matching the `hooks/waveform-utils.ts` /
  `hooks/sentiment-utils.ts` convention (vitest is pure-TS only; RN components are not
  unit-testable here).

## Design

### Component

A new self-contained `ResponseLookupCue({ appVariant, reduceMotion, styles })` in
`app/index.tsx`, alongside `RecordingLevelMeter` and `PrivateProcessingCue`. It replaces
the bare text block in the `responseLookup` branch. It reuses the existing
`processingHalo`, `processingCore`, and `processingTitle` styles so it reads as a
continuation of the processing screen.

### Animation (React Native `Animated`)

Mirror the existing pulse pattern (`app/index.tsx:275-306`): hold `Animated.Value`s in
`useRef`, start the loops in a `useEffect`, and stop/reset them in its cleanup.

- **Rotating core ring:** a `0 → 1` linear `Animated.loop` (~1200ms), interpolated to
  `0deg → 360deg` and applied as a `rotate` transform on the core. Because `processingCore`
  already has one accent-colored edge (`borderTopColor: colors.accent` over a
  `colors.primary` ring), rotating it produces a genuine spinner.
- **Pulsing halo:** scale `1 → 1.06 → 1` (~900ms in/out, `Easing.inOut(Easing.ease)`),
  echoing the recording-screen pulse.
- Both use `useNativeDriver: true`.

### Cycling caption

A variant-aware list advanced every `LOOKUP_CAPTION_INTERVAL_MS = 2000`ms via a
`setInterval`, **clamped at the last line** (holds on the final line; does not loop, so it
never implies false repeated progress). The list, given the variant's response noun
(`RESPONSE_NOUN_LABELS`: `verse` for christian, `passage` for stoic/dhammapada):

1. `Finding your {noun}`
2. `Reading your reflection`
3. `Choosing a fitting {noun}`
4. `Almost there…`

Below the cycling caption, one fixed reassurance line reinforcing the privacy model during
the only outbound network call:

> Only your private summary was sent — no audio or transcript.

The caption index is component state; the interval is created in a `useEffect` and cleared
on unmount. If the lookup settles quickly, the component unmounts and only the first line
is seen — which is fine.

### Reduce-motion

When `reduceMotion` is true, the rotation and pulse loops do not start (static halo + ring,
matching how the recording pulse is gated). The caption still advances — it is progress
text, not vestibular motion — so the screen stays informative without animation.

### Testable seam

Extract a pure helper into `hooks/lookup-cue.ts`:

```ts
export function buildLookupCaptions(noun: string): string[]
```

Returns the four-line list above with `{noun}` substituted. Unit-tested in
`hooks/__tests__/lookup-cue.test.ts` (asserts the exact lines and noun substitution for at
least two nouns). The animation/interval wiring stays in the component and is verified
on-device.

## Files touched

- Create: `hooks/lookup-cue.ts`, `hooks/__tests__/lookup-cue.test.ts`
- Modify: `app/index.tsx` — add `ResponseLookupCue`, swap it into the `responseLookup`
  branch, add timing constant, new styles only if the reused processing styles are
  insufficient (e.g. a caption/subtext style).

## Out of scope

- Any change to the lookup request, provider chain, backend, or transcription/sentiment
  pipeline.
- Animating the existing `PrivateProcessingCue` (processing state) — unchanged.

## Verification

- `npm run typecheck`, `npm run lint`, `npm test` (covers `buildLookupCaptions`).
- Manual on-device (both variants): the `responseLookup` screen shows a spinning ring +
  pulsing halo with a caption that cycles every ~2s and holds on the last line; the verse
  noun matches the variant; with Reduce Motion enabled the ring/halo are static while the
  caption still advances.
