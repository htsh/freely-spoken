# Recording Screen: Scrolling Waveform + Keep-Awake Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the recording-screen level meter visibly react to the user's voice (scrolling waveform), keep the screen awake while recording, and auto-stop recording at 90s.

**Architecture:** A pure, unit-tested `pushSample` helper maintains a fixed-length history buffer of smoothed input levels; `RecordingLevelMeter` renders that buffer as a left-scrolling row of thin bars (with a calm, non-scrolling fallback under reduce-motion). Two effects in `HomeScreen` hold an `expo-keep-awake` lock during the working states and auto-invoke the existing `handleStop()` at the duration cap.

**Tech Stack:** Expo / React Native (TypeScript strict), `expo-av` (existing recorder, single overall dB level only), `expo-keep-awake` (new), vitest (pure-TS tests only).

**Spec:** `docs/superpowers/specs/2026-06-06-recording-screen-waveform-and-keep-awake-design.md`

**Key constraints (do not violate):**
- Privacy allowlist is untouched. `duration` stays local; nothing new enters the lookup request. Do not modify `services/lookup-request.ts` or its test.
- `hooks/use-audio-recorder.ts` is RN/native and NOT unit-testable; only the pure `pushSample` helper gets a vitest test.
- `ios/` is generated and git-ignored — never edit it. The new native dependency needs `npx expo run:ios` to take effect.

---

### Task 1: Pure waveform history helper (`pushSample`)

**Files:**
- Create: `hooks/waveform-utils.ts`
- Test: `hooks/__tests__/waveform-utils.test.ts`

- [ ] **Step 1: Write the failing test**

Create `hooks/__tests__/waveform-utils.test.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { emptyHistory, pushSample } from '../waveform-utils';

describe('emptyHistory', () => {
  it('returns an array of the requested length filled with zeros', () => {
    expect(emptyHistory(4)).toEqual([0, 0, 0, 0]);
  });
});

describe('pushSample', () => {
  it('appends the newest sample at the end and keeps the array full-width', () => {
    const result = pushSample([0, 0, 0, 0], 0.5, 4);
    expect(result).toEqual([0, 0, 0, 0.5]);
  });

  it('drops the oldest sample from the left when at capacity', () => {
    const result = pushSample([0.1, 0.2, 0.3, 0.4], 0.9, 4);
    expect(result).toEqual([0.2, 0.3, 0.4, 0.9]);
  });

  it('left-pads with zeros when the history is shorter than size', () => {
    const result = pushSample([], 0.7, 3);
    expect(result).toEqual([0, 0, 0.7]);
  });

  it('clamps out-of-range levels into [0, 1]', () => {
    expect(pushSample([0, 0], 1.8, 2)).toEqual([0, 1]);
    expect(pushSample([0, 0], -0.5, 2)).toEqual([0, 0]);
  });

  it('treats non-finite levels as 0', () => {
    expect(pushSample([0.4, 0.4], Number.NaN, 2)).toEqual([0.4, 0]);
  });

  it('does not mutate the input array', () => {
    const input = [0.1, 0.2];
    pushSample(input, 0.3, 2);
    expect(input).toEqual([0.1, 0.2]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run hooks/__tests__/waveform-utils.test.ts`
Expected: FAIL — cannot find module `../waveform-utils`.

- [ ] **Step 3: Write minimal implementation**

Create `hooks/waveform-utils.ts`:

```ts
// Pure helpers for the recording-screen waveform meter.
// No React or React Native dependencies — testable in any JS runtime.

export function emptyHistory(size: number): number[] {
  return new Array(size).fill(0);
}

// Append `level` to the rolling history and return a new array of length `size`
// (oldest sample dropped on the left, left-padded with zeros if too short).
// `level` is clamped to [0, 1]; non-finite values become 0.
export function pushSample(history: number[], level: number, size: number): number[] {
  const clamped = Number.isFinite(level) ? Math.max(0, Math.min(1, level)) : 0;
  const next = [...history, clamped];
  if (next.length > size) {
    return next.slice(next.length - size);
  }
  if (next.length < size) {
    return [...new Array(size - next.length).fill(0), ...next];
  }
  return next;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run hooks/__tests__/waveform-utils.test.ts`
Expected: PASS (all cases).

- [ ] **Step 5: Commit**

```bash
git add hooks/waveform-utils.ts hooks/__tests__/waveform-utils.test.ts
git commit -m "feat: add pure pushSample helper for waveform meter"
```

---

### Task 2: Rewrite `RecordingLevelMeter` as a scrolling waveform

**Files:**
- Modify: `app/index.tsx` (constants near line 52-54; component at 67-96; call site at 321; styles `levelMeterBar` near 730)

UI component — not unit-testable. Verify with `typecheck` + `lint`.

- [ ] **Step 1: Add the waveform-utils import**

In `app/index.tsx`, near the other `@/` imports (e.g. just after the `useAudioRecorder` import on line 9), add:

```ts
import { emptyHistory, pushSample } from '@/hooks/waveform-utils';
```

- [ ] **Step 2: Replace the meter constants**

Replace lines 52-54:

```ts
const METER_BAR_COUNT = 5;
const METER_BAR_MIN_HEIGHT = 6;
const METER_BAR_HEIGHT_RANGE = 20;
```

with:

```ts
const WAVEFORM_BAR_COUNT = 28;
const WAVEFORM_BAR_MIN_HEIGHT = 4;
const WAVEFORM_BAR_HEIGHT_RANGE = 22;
```

- [ ] **Step 3: Rewrite the `RecordingLevelMeter` component**

Replace the whole component (lines 67-96) with:

```tsx
function RecordingLevelMeter({
  inputLevel,
  reduceMotion,
  styles,
}: {
  inputLevel: number;
  reduceMotion: boolean;
  styles: HomeStyles;
}) {
  const [history, setHistory] = useState<number[]>(() => emptyHistory(WAVEFORM_BAR_COUNT));

  useEffect(() => {
    if (reduceMotion) return;
    setHistory((prev) => pushSample(prev, inputLevel, WAVEFORM_BAR_COUNT));
  }, [inputLevel, reduceMotion]);

  // Reduce-motion: a calm, non-scrolling row — every bar reflects the current
  // level only (height changes in place, no horizontal movement).
  const levels = reduceMotion
    ? new Array(WAVEFORM_BAR_COUNT).fill(Math.max(0, Math.min(1, inputLevel)))
    : history;

  return (
    <View
      style={styles.levelMeter}
      accessible
      accessibilityRole="image"
      accessibilityLabel="Live microphone input level"
    >
      {levels.map((level, index) => (
        <View
          key={`meter-bar-${index}`}
          style={[
            styles.levelMeterBar,
            { height: WAVEFORM_BAR_MIN_HEIGHT + level * WAVEFORM_BAR_HEIGHT_RANGE },
          ]}
        />
      ))}
    </View>
  );
}
```

- [ ] **Step 4: Update the call site**

At the recording block (currently line 321), replace:

```tsx
<RecordingLevelMeter inputLevel={inputLevel} styles={styles} />
```

with:

```tsx
<RecordingLevelMeter inputLevel={inputLevel} reduceMotion={reduceMotionEnabled} styles={styles} />
```

- [ ] **Step 5: Narrow the bars in styles**

In `buildStyles`, the `levelMeterBar` style (near line 730) is currently:

```ts
  levelMeterBar: {
    width: 6,
    borderRadius: 4,
    marginHorizontal: 2,
    backgroundColor: colors.destructive,
  },
```

Replace with (thinner bars + tighter gap so 28 fit; ~28 × (3 + 2) ≈ 140px wide):

```ts
  levelMeterBar: {
    width: 3,
    borderRadius: 2,
    marginHorizontal: 1,
    backgroundColor: colors.destructive,
  },
```

Leave the `levelMeter` container style (height 30, `flexDirection: 'row'`, `alignItems: 'flex-end'`) unchanged — max bar height is `4 + 22 = 26`, which fits.

- [ ] **Step 6: Verify types and lint**

Run: `npm run typecheck && npm run lint`
Expected: both pass. (If `typecheck` reports the old `METER_BAR_*` constants as unused/undefined anywhere, ensure all three references were replaced.)

- [ ] **Step 7: Commit**

```bash
git add app/index.tsx
git commit -m "feat: scrolling waveform recording meter with reduce-motion fallback"
```

---

### Task 3: Keep the screen awake during the working states

**Files:**
- Modify: `package.json` (add `expo-keep-awake`)
- Modify: `app/index.tsx` (import + new effect in `HomeScreen`)

Native dependency — `npm test`/`typecheck` validate wiring; physical sleep behavior is verified on-device in Task 5.

- [ ] **Step 1: Install the dependency (SDK-pinned)**

Run: `npx expo install expo-keep-awake`
Expected: `expo-keep-awake` added to `package.json` dependencies at an SDK-compatible version.

- [ ] **Step 2: Add the import**

In `app/index.tsx`, with the other package imports, add:

```ts
import { activateKeepAwakeAsync, deactivateKeepAwake } from 'expo-keep-awake';
```

- [ ] **Step 3: Add a keep-awake tag constant**

Near the other module-level constants in `app/index.tsx`, add:

```ts
const KEEP_AWAKE_TAG = 'recording-flow';
```

- [ ] **Step 4: Add the keep-awake effect**

Inside `HomeScreen`, alongside the other `useEffect`s, add:

```tsx
useEffect(() => {
  const working =
    appState === 'recording' ||
    appState === 'processing' ||
    appState === 'responseLookup';
  if (!working) return;

  activateKeepAwakeAsync(KEEP_AWAKE_TAG);
  return () => {
    deactivateKeepAwake(KEEP_AWAKE_TAG);
  };
}, [appState]);
```

- [ ] **Step 5: Verify types and tests**

Run: `npm run typecheck && npm test`
Expected: typecheck passes; vitest suite passes (no behavior change to pure tests).

- [ ] **Step 6: Commit**

```bash
git add package.json package-lock.json app/index.tsx
git commit -m "feat: keep screen awake while recording and processing"
```

---

### Task 4: Auto-stop recording at 90s + wrap-up hint

**Files:**
- Modify: `app/index.tsx` (constants, new effect, recording-hint text near line 322)

UI/behavior — verified by `typecheck`/`lint` here and on-device in Task 5.

- [ ] **Step 1: Add the cap constants**

Near the other module-level constants in `app/index.tsx`, add:

```ts
const MAX_RECORDING_SECONDS = 90;
const WRAP_UP_WARNING_SECONDS = 10;
```

- [ ] **Step 2: Add the auto-stop effect**

Inside `HomeScreen`, after `handleStop` is defined, add:

```tsx
useEffect(() => {
  if (appState !== 'recording') return;
  if (duration >= MAX_RECORDING_SECONDS) {
    handleStop();
  }
}, [appState, duration, handleStop]);
```

(`duration` and `handleStop` are already in scope — `duration` comes from `useAudioRecorder()` and `handleStop` is the existing stop handler bound to the stop button. The `appState === 'recording'` guard ensures this fires once, since `handleStop` moves state to `processing`.)

- [ ] **Step 3: Soften the recording hint near the cap**

In the recording block, replace the hint (currently line 322):

```tsx
<ThemedText style={styles.hint}>Recording...</ThemedText>
```

with:

```tsx
<ThemedText style={styles.hint}>
  {duration >= MAX_RECORDING_SECONDS - WRAP_UP_WARNING_SECONDS
    ? 'Wrapping up soon…'
    : 'Recording...'}
</ThemedText>
```

- [ ] **Step 4: Verify types and lint**

Run: `npm run typecheck && npm run lint`
Expected: both pass.

- [ ] **Step 5: Commit**

```bash
git add app/index.tsx
git commit -m "feat: auto-stop recording at 90s with wrap-up hint"
```

---

### Task 5: Full verification

**Files:** none (validation only)

- [ ] **Step 1: Run the full pure-TS gate**

Run: `npm run typecheck && npm run lint && npm test`
Expected: all pass, including `waveform-utils.test.ts`.

- [ ] **Step 2: Manual on-device check (both variants)**

A native rebuild is required to pick up `expo-keep-awake`.

Run: `npx expo run:ios --device`
Then repeat with: `EXPO_PUBLIC_APP_VARIANT=dhammapada npx expo run:ios --device`

Confirm, while recording:
- The meter shows a left-scrolling waveform and **all** bars move with speech (no pinned-left bars).
- With Reduce Motion enabled (iOS Settings → Accessibility → Motion), the meter shows the calm in-place level (no scrolling), and the stop-button pulse halo stays suppressed as before.
- The screen does **not** sleep / enter screensaver while recording or processing.
- Recording auto-stops at 90s and flows into processing; the hint reads "Wrapping up soon…" in the final ~10s.

- [ ] **Step 3: Confirm privacy contract is untouched**

Run: `npx vitest run services/__tests__/lookup-request.test.ts`
Expected: PASS unchanged — confirms no new fields entered the lookup request.
