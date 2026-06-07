# Animated Verse-Lookup Loader (`ResponseLookupCue`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the bare "Finding a response..." text in the `responseLookup` state with an animated cue — a spinning ring + pulsing halo and a cycling, variant-aware caption — that matches the existing processing screen.

**Architecture:** A pure `buildLookupCaptions(noun)` helper (unit-tested) supplies the caption list. A new self-contained `ResponseLookupCue` component in `app/index.tsx` reuses the existing `processingHalo`/`processingCore`/`processingTitle`/`processingPrivacyText` styles, animates them with React Native `Animated` (gated on reduce-motion, mirroring the existing recording-pulse effect), and cycles the caption with a clamped `setInterval`.

**Tech Stack:** Expo / React Native (TypeScript strict), RN `Animated` (already imported in `app/index.tsx`), vitest (pure-TS tests only).

**Spec:** `docs/superpowers/specs/2026-06-06-response-lookup-cue-design.md`

**Key constraints (do not violate):**
- Purely presentational. Do NOT change the lookup request, provider chain, or any network field. Do not touch `services/`.
- Reduce-motion must disable the spin/pulse loops (the caption may still advance).
- RN components are not unit-testable here; only `buildLookupCaptions` gets a vitest test.
- We are committing directly to `main` (user is working on main).

---

### Task 1: Pure caption helper (`buildLookupCaptions`)

**Files:**
- Create: `hooks/lookup-cue.ts`
- Test: `hooks/__tests__/lookup-cue.test.ts`

- [ ] **Step 1: Write the failing test**

Create `hooks/__tests__/lookup-cue.test.ts`. NOTE: the last line uses a single Unicode ellipsis character `…` (U+2026), not three dots.

```ts
import { describe, it, expect } from 'vitest';
import { buildLookupCaptions } from '../lookup-cue';

describe('buildLookupCaptions', () => {
  it('substitutes the noun into the first and third lines (verse)', () => {
    expect(buildLookupCaptions('verse')).toEqual([
      'Finding your verse',
      'Reading your reflection',
      'Choosing a fitting verse',
      'Almost there…',
    ]);
  });

  it('substitutes the noun into the first and third lines (passage)', () => {
    expect(buildLookupCaptions('passage')).toEqual([
      'Finding your passage',
      'Reading your reflection',
      'Choosing a fitting passage',
      'Almost there…',
    ]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run hooks/__tests__/lookup-cue.test.ts`
Expected: FAIL — cannot find module `../lookup-cue`.

- [ ] **Step 3: Write minimal implementation**

Create `hooks/lookup-cue.ts` (the last list entry uses the Unicode ellipsis `…`):

```ts
// Pure helper for the response-lookup loading cue. No React or React Native
// dependencies — testable in any JS runtime.

// Caption lines shown (and cycled) while the backend selects a passage.
// `noun` is the variant's response noun, e.g. 'verse' or 'passage'.
export function buildLookupCaptions(noun: string): string[] {
  return [
    `Finding your ${noun}`,
    'Reading your reflection',
    `Choosing a fitting ${noun}`,
    'Almost there…',
  ];
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run hooks/__tests__/lookup-cue.test.ts`
Expected: PASS (both cases).

- [ ] **Step 5: Commit**

```bash
git add hooks/lookup-cue.ts hooks/__tests__/lookup-cue.test.ts
git commit -m "feat: add buildLookupCaptions helper for verse-lookup cue"
```

---

### Task 2: `ResponseLookupCue` component + swap into the responseLookup branch

**Files:**
- Modify: `app/index.tsx`

UI/animation — not unit-testable. Verify with `npm run typecheck` and `npm run lint`.

**Context for the implementer (already true in the file, do not re-add):**
- `Animated` and `Easing` are imported from `react-native` (line ~3).
- `useState`, `useEffect`, `useRef`, `useMemo` are imported from `react` (line 1).
- `ThemedText` is imported. `AppVariant` is imported from `@/services/lookup-client`.
- `RESPONSE_NOUN_LABELS: Record<AppVariant, string>` is defined at module scope (`verse` for christian, `passage` for stoic/dhammapada).
- `HomeStyles = ReturnType<typeof buildStyles>`.
- These styles already exist in `buildStyles` and are reused as-is: `processingPanel`, `processingHalo`, `processingCore`, `processingTitle`, `processingPrivacyText`, `center`.
- The existing recording-pulse effect (around line 275) is the pattern to mirror for animation lifecycle (start in effect, stop + reset value in cleanup, gate on reduce-motion).

- [ ] **Step 1: Add the import for the caption helper**

Near the other `@/hooks/...` imports (e.g. just after `import { emptyHistory, pushSample } from '@/hooks/waveform-utils';`), add:

```ts
import { buildLookupCaptions } from '@/hooks/lookup-cue';
```

- [ ] **Step 2: Add the caption-interval constant**

Near the other module-level constants (e.g. right after `const KEEP_AWAKE_TAG = 'recording-flow';`), add:

```ts
const LOOKUP_CAPTION_INTERVAL_MS = 2000;
```

- [ ] **Step 3: Add the `ResponseLookupCue` component**

Add this component near the other cue components (e.g. directly after the `RecordingLevelMeter` component definition, before `export default function HomeScreen`):

```tsx
function ResponseLookupCue({
  appVariant,
  reduceMotion,
  styles,
}: {
  appVariant: AppVariant;
  reduceMotion: boolean;
  styles: HomeStyles;
}) {
  const captions = useMemo(
    () => buildLookupCaptions(RESPONSE_NOUN_LABELS[appVariant]),
    [appVariant],
  );
  const [captionIndex, setCaptionIndex] = useState(0);

  const rotate = useRef(new Animated.Value(0)).current;
  const haloPulse = useRef(new Animated.Value(1)).current;

  // Advance the caption every interval, clamped at the last line (no loop).
  useEffect(() => {
    if (captionIndex >= captions.length - 1) return;
    const id = setInterval(() => {
      setCaptionIndex((prev) => Math.min(prev + 1, captions.length - 1));
    }, LOOKUP_CAPTION_INTERVAL_MS);
    return () => clearInterval(id);
  }, [captionIndex, captions.length]);

  useEffect(() => {
    if (reduceMotion) {
      rotate.stopAnimation();
      rotate.setValue(0);
      haloPulse.stopAnimation();
      haloPulse.setValue(1);
      return;
    }

    const spin = Animated.loop(
      Animated.timing(rotate, {
        toValue: 1,
        duration: 1200,
        easing: Easing.linear,
        useNativeDriver: true,
      }),
    );
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(haloPulse, {
          toValue: 1.06,
          duration: 900,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(haloPulse, {
          toValue: 1,
          duration: 900,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
      ]),
    );

    spin.start();
    pulse.start();

    return () => {
      spin.stop();
      pulse.stop();
      rotate.stopAnimation();
      rotate.setValue(0);
      haloPulse.stopAnimation();
      haloPulse.setValue(1);
    };
  }, [reduceMotion, rotate, haloPulse]);

  const spinDeg = rotate.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '360deg'],
  });

  return (
    <View style={styles.processingPanel}>
      <Animated.View style={[styles.processingHalo, { transform: [{ scale: haloPulse }] }]}>
        <Animated.View
          style={[styles.processingCore, { transform: [{ rotate: spinDeg }] }]}
        />
      </Animated.View>
      <ThemedText type="subtitle" style={styles.processingTitle}>
        {captions[captionIndex]}
      </ThemedText>
      <ThemedText style={styles.processingPrivacyText}>
        Only your private summary was sent — no audio or transcript.
      </ThemedText>
    </View>
  );
}
```

- [ ] **Step 4: Swap it into the `responseLookup` branch**

Find this block (currently around line 393):

```tsx
{appState === 'responseLookup' && (
  <View style={styles.center}>
    <ThemedText>Finding a response...</ThemedText>
  </View>
)}
```

Replace with:

```tsx
{appState === 'responseLookup' && (
  <View style={styles.center}>
    <ResponseLookupCue
      appVariant={appVariant}
      reduceMotion={reduceMotionEnabled}
      styles={styles}
    />
  </View>
)}
```

(`appVariant` and `reduceMotionEnabled` are already in scope in `HomeScreen`.)

- [ ] **Step 5: Verify types and lint**

Run: `npm run typecheck && npm run lint`
Expected: both pass with zero errors and zero warnings. If lint warns about a missing `useEffect`/`useMemo` dependency, re-check the dependency arrays against the code above (they are intentionally complete: `[captionIndex, captions.length]` and `[reduceMotion, rotate, haloPulse]`).

- [ ] **Step 6: Commit**

```bash
git add app/index.tsx
git commit -m "feat: animated cue for the verse-lookup state"
```

---

### Task 3: Full verification

**Files:** none (validation only)

- [ ] **Step 1: Run the full pure-TS gate**

Run: `npm run typecheck && npm run lint && npm test`
Expected: all pass, including the new `lookup-cue.test.ts` (total test count increases by 2).

- [ ] **Step 2: Confirm the network/privacy contract is untouched**

Run: `npx vitest run services/__tests__/lookup-request.test.ts`
Expected: PASS unchanged — this change is presentational and must not alter the outbound request.

- [ ] **Step 3: Manual on-device check (both variants)**

Run: `npx expo run:ios --device`
Then repeat with: `EXPO_PUBLIC_APP_VARIANT=dhammapada npx expo run:ios --device`

Drive the flow to the lookup step (record → review → find response). Confirm:
- The `responseLookup` screen shows the halo with a spinning core ring and a gently pulsing halo.
- The caption cycles roughly every 2s (`Finding your verse/passage` → `Reading your reflection` → `Choosing a fitting verse/passage` → `Almost there…`) and holds on the last line.
- The noun matches the variant (christian: "verse"; Idle Ashes/dhammapada: "passage").
- The reassurance line "Only your private summary was sent — no audio or transcript." is shown.
- With Reduce Motion enabled (iOS Settings → Accessibility → Motion), the ring/halo are static while the caption still advances.
