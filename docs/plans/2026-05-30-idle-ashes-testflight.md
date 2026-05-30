# Idle Ashes TestFlight Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prepare Idle Ashes as a branded Dhammapada iOS app variant that can be submitted to internal TestFlight as a separate App Store Connect app and separate EAS project.

**Architecture:** Keep one repository and one shared backend. Use `EXPO_PUBLIC_APP_VARIANT=dhammapada` to select Idle Ashes native identity, EAS project metadata, assets, brand tokens, and UI styling while preserving Freely Spoken defaults. The backend remains `https://verses.hitesh.nyc`; the app sends `appVariant: "dhammapada"` and the existing FastAPI service routes to the Dhammapada catalog adapter.

**Tech Stack:** Expo SDK 54, React Native 0.81, TypeScript, expo-router, Swift/AppKit asset generator, EAS Build/Submit, FastAPI backend on VPS behind Caddy.

---

### Task 1: Create Implementation Branch And Baseline

**Files:**
- Read: `docs/superpowers/specs/2026-05-30-idle-ashes-testflight-design.md`
- Read: `app.config.js`
- Read: `constants/brand.ts`
- Read: `app/index.tsx`

**Step 1: Create a working branch**

Run:

```bash
git switch -c codex/idle-ashes-testflight
```

Expected: branch switches from `main` to `codex/idle-ashes-testflight`.

**Step 2: Confirm clean starting point**

Run:

```bash
git status --short
```

Expected: no output.

**Step 3: Run baseline tests**

Run:

```bash
npm test
npm run typecheck
```

Expected: both pass before implementation. If either fails, capture the failure and decide whether it is pre-existing before editing.

---

### Task 2: Generate Idle Ashes Brand Assets

**Files:**
- Modify: `tools/branding/generate-freely-spoken-assets.swift`
- Modify: `assets/brand/README.md`
- Create: `assets/brand/idle-ashes-mark.svg`
- Create: `assets/brand/idle-ashes-wordmark.svg`
- Create: `assets/brand/idle-ashes-lockup.svg`
- Create: `assets/brand/idle-ashes-mark.png`
- Create: `assets/brand/idle-ashes-wordmark.png`
- Create: `assets/brand/idle-ashes-lockup.png`
- Create: `assets/images/idle-ashes-icon.png`
- Create: `assets/images/idle-ashes-splash-icon.png`
- Create: `assets/images/idle-ashes-favicon.png`
- Create: `assets/images/idle-ashes-android-icon-background.png`
- Create: `assets/images/idle-ashes-android-icon-foreground.png`
- Create: `assets/images/idle-ashes-android-icon-monochrome.png`

**Step 1: Add Idle Ashes brand constants**

In `tools/branding/generate-freely-spoken-assets.swift`, keep the existing `Brand` enum for Freely Spoken and add a second enum:

```swift
private enum IdleAshesBrand {
  static let name = "Idle Ashes"
  static let charcoalHex = "#2B2A25"
  static let ashHex = "#7C756B"
  static let ivoryHex = "#F4EEE6"
  static let clayHex = "#A66036"
  static let emberHex = "#C1784A"
  static let panelHex = "#E9DFD2"
  static let inkHex = "#24231F"

  static let charcoal = NSColor(hex: 0x2B2A25)
  static let ash = NSColor(hex: 0x7C756B)
  static let ivory = NSColor(hex: 0xF4EEE6)
  static let clay = NSColor(hex: 0xA66036)
  static let ember = NSColor(hex: 0xC1784A)
  static let panel = NSColor(hex: 0xE9DFD2)
  static let ink = NSColor(hex: 0x24231F)
}
```

**Step 2: Add vector-friendly Idle Ashes drawing helpers**

Add functions beside the Freely Spoken drawing helpers:

```swift
private func drawIdleAshesMark(
  in rect: NSRect,
  markColor: NSColor = IdleAshesBrand.charcoal,
  accentColor: NSColor = IdleAshesBrand.ember,
  includeAccent: Bool = true
) {
  let side = min(rect.width, rect.height)
  let scale = side / 256
  let origin = NSPoint(x: rect.midX - side / 2, y: rect.midY - side / 2)

  func path(_ points: [(CGFloat, CGFloat)], close: Bool = true) -> NSBezierPath {
    let p = NSBezierPath()
    p.move(to: point(points[0].0, points[0].1, origin, scale))
    for item in points.dropFirst() {
      p.line(to: point(item.0, item.1, origin, scale))
    }
    if close { p.close() }
    return p
  }

  let fragments: [[(CGFloat, CGFloat)]] = [
    [(123, 22), (149, 44), (139, 76), (109, 82), (91, 56), (101, 31)],
    [(73, 82), (101, 100), (94, 132), (63, 142), (44, 117), (50, 91)],
    [(157, 84), (188, 98), (194, 132), (169, 154), (139, 143), (134, 111)],
    [(96, 151), (132, 142), (157, 166), (145, 199), (108, 207), (82, 184)],
    [(154, 170), (190, 159), (211, 184), (199, 219), (162, 229), (137, 204)],
  ]

  for (index, fragment) in fragments.enumerated() {
    let alpha = index == 0 ? 0.34 : 1
    markColor.withAlphaComponent(alpha).setFill()
    path(fragment).fill()
  }

  if includeAccent {
    let ember = NSBezierPath(ovalIn: NSRect(
      x: origin.x + 117 * scale,
      y: origin.y + 136 * scale,
      width: 24 * scale,
      height: 24 * scale
    ))
    accentColor.setFill()
    ember.fill()
  }
}

private func drawIdleAshesWordmark(canvasWidth: CGFloat, topY: CGFloat, size: CGFloat) {
  _ = drawCenteredText(
    "idle ashes",
    y: topY,
    size: size,
    color: IdleAshesBrand.ink,
    canvasWidth: canvasWidth
  )
}
```

During implementation, tune the fragment points if rendered previews look too much like a flower or bowl. Keep five or fewer fragments.

**Step 3: Add Idle Ashes raster output**

Extend `writeRasterAssets()` to write variant-specific files without changing the existing Freely Spoken filenames:

```swift
try writePNG(width: 1024, height: 1024, background: IdleAshesBrand.ivory, hasAlpha: false, to: imageURL.appendingPathComponent("idle-ashes-icon.png")) {
  IdleAshesBrand.ivory.setFill()
  NSRect(x: 0, y: 0, width: 1024, height: 1024).fill()
  drawIdleAshesMark(in: NSRect(x: 246, y: 180, width: 532, height: 532))
}
try flattenOpaquePNG(at: imageURL.appendingPathComponent("idle-ashes-icon.png"), background: IdleAshesBrand.ivory)

try writePNG(width: 1024, height: 1024, background: IdleAshesBrand.ivory, hasAlpha: false, to: imageURL.appendingPathComponent("idle-ashes-splash-icon.png")) {
  drawIdleAshesMark(in: NSRect(x: 386, y: 170, width: 252, height: 252))
  drawIdleAshesWordmark(canvasWidth: 1024, topY: 442, size: 132)
}
try flattenOpaquePNG(at: imageURL.appendingPathComponent("idle-ashes-splash-icon.png"), background: IdleAshesBrand.ivory)
```

Also generate `idle-ashes-favicon.png`, `idle-ashes-android-icon-background.png`, `idle-ashes-android-icon-foreground.png`, `idle-ashes-android-icon-monochrome.png`, and brand PNGs with the same mark function.

**Step 4: Add Idle Ashes SVG output**

Add `idleAshesMarkSVG()`, `idleAshesWordmarkSVG()`, and `idleAshesLockupSVG()` functions. Keep paths flat and compatible with a future designer/vector pass.

**Step 5: Run the generator**

Run:

```bash
swift tools/branding/generate-freely-spoken-assets.swift
```

Expected: existing Freely Spoken assets are regenerated and new Idle Ashes assets appear.

**Step 6: Inspect generated asset dimensions**

Run:

```bash
sips -g pixelWidth -g pixelHeight assets/images/idle-ashes-icon.png assets/images/idle-ashes-splash-icon.png assets/brand/idle-ashes-lockup.png
```

Expected: icon and splash are `1024 x 1024`; lockup is wide, matching generator output.

**Step 7: Commit**

Run:

```bash
git add tools/branding/generate-freely-spoken-assets.swift assets/brand assets/images
git commit -m "Add Idle Ashes brand assets"
```

---

### Task 3: Wire Idle Ashes Native Identity And EAS Metadata

**Files:**
- Modify: `app.config.js`
- Modify: `eas.json`

**Step 1: Add variant asset paths and slug support**

In `app.config.js`, add helper values:

```js
const FREELY_SPOKEN_EAS_PROJECT_ID = '9af03ee3-2eae-4f5c-b0fe-60200c3bd29d';
const IDLE_ASHES_EAS_PROJECT_ID = process.env.IDLE_ASHES_EAS_PROJECT_ID;
```

Update `VARIANTS.dhammapada`:

```js
dhammapada: {
  name: 'Idle Ashes',
  slug: 'idle-ashes',
  iosBundleId: 'com.htsh.idleashes',
  androidPackage: 'com.htsh.idleashes',
  scheme: 'idleashes',
  icon: './assets/images/idle-ashes-icon.png',
  splashImage: './assets/images/idle-ashes-splash-icon.png',
  splashBackgroundColor: '#F4EEE6',
  androidAdaptiveIcon: {
    foregroundImage: './assets/images/idle-ashes-android-icon-foreground.png',
    backgroundImage: './assets/images/idle-ashes-android-icon-background.png',
    monochromeImage: './assets/images/idle-ashes-android-icon-monochrome.png',
    backgroundColor: '#F4EEE6',
  },
  favicon: './assets/images/idle-ashes-favicon.png',
  easProjectId: IDLE_ASHES_EAS_PROJECT_ID,
}
```

Add equivalent explicit fields for `christian`, using the existing Freely Spoken paths and `FREELY_SPOKEN_EAS_PROJECT_ID`.

**Step 2: Apply the variant fields**

In the exported function, after resolving `variant`, set:

```js
config.slug = variant.slug;
config.icon = variant.icon;
config.web = { ...(config.web || {}), favicon: variant.favicon };
config.android = {
  ...(config.android || {}),
  package: variant.androidPackage,
  adaptiveIcon: {
    ...(config.android?.adaptiveIcon || {}),
    ...(variant.androidAdaptiveIcon || {}),
  },
};
```

Update the `expo-splash-screen` plugin options inside the existing plugin map:

```js
if (name === 'expo-splash-screen') {
  return [name, {
    ...next,
    image: variant.splashImage,
    backgroundColor: variant.splashBackgroundColor,
    dark: {
      ...(next.dark || {}),
      backgroundColor: variant.splashBackgroundColor,
    },
  }];
}
```

When setting `config.extra`, preserve router data and set the EAS project id dynamically:

```js
config.extra = {
  ...(config.extra || {}),
  eas: {
    ...(config.extra?.eas || {}),
    projectId: variant.easProjectId || config.extra?.eas?.projectId,
  },
  lookupApiUrl,
  lookupClientSecret,
  appVariant,
};
```

**Step 3: Add Idle Ashes build env**

In `eas.json`, update both Idle Ashes profiles to include URL and secret placeholders pulled from EAS environment variables, not committed literals:

```json
"production-idleashes": {
  "distribution": "store",
  "environment": "production",
  "env": {
    "EXPO_PUBLIC_APP_VARIANT": "dhammapada",
    "EXPO_PUBLIC_LOOKUP_API_URL": "https://verses.hitesh.nyc"
  },
  "ios": {
    "buildConfiguration": "Release"
  }
}
```

Do not commit `EXPO_PUBLIC_LOOKUP_CLIENT_SECRET` into `eas.json`. Configure it through EAS environment/secrets or local `.env`.

**Step 4: Verify config for Freely Spoken**

Run:

```bash
npx expo config --json > /tmp/freely-spoken-config.json
node -e "const c=require('/tmp/freely-spoken-config.json'); console.log(c.name, c.slug, c.ios.bundleIdentifier, c.extra.eas.projectId)"
```

Expected:

```text
Freely Spoken mic-check com.htsh.miccheck 9af03ee3-2eae-4f5c-b0fe-60200c3bd29d
```

**Step 5: Verify config for Idle Ashes without project id**

Run:

```bash
EXPO_PUBLIC_APP_VARIANT=dhammapada npx expo config --json > /tmp/idle-ashes-config.json
node -e "const c=require('/tmp/idle-ashes-config.json'); console.log(c.name, c.slug, c.ios.bundleIdentifier, c.icon)"
```

Expected:

```text
Idle Ashes idle-ashes com.htsh.idleashes ./assets/images/idle-ashes-icon.png
```

If `extra.eas.projectId` still shows the Freely Spoken id for Idle Ashes before the new EAS project is created, do not build yet. Continue to the EAS project task.

**Step 6: Commit**

Run:

```bash
git add app.config.js eas.json
git commit -m "Wire Idle Ashes app identity"
```

---

### Task 4: Add Variant-Aware Brand Tokens

**Files:**
- Modify: `constants/brand.ts`
- Modify: `constants/theme.ts`
- Modify: `hooks/use-theme-color.ts`
- Test: `services/__tests__/lookup-request.test.ts` only if adding variant tests there is useful; otherwise create `constants/__tests__/brand.test.ts`

**Step 1: Add brand token types**

Replace the single shared `Brand.colors` export in `constants/brand.ts` with variant-aware token exports:

```ts
import type { AppVariant } from '@/services/lookup-request';

export type BrandPalette = {
  primary: string;
  accent: string;
  background: string;
  surface: string;
  softSurface: string;
  text: string;
  muted: string;
  destructive: string;
  darkSurface: string;
  inverseText: string;
};

export type BrandTokens = {
  name: string;
  wordmark: string;
  colors: BrandPalette;
};
```

Define:

```ts
const BRANDS: Record<AppVariant, BrandTokens> = {
  christian: {
    name: 'Freely Spoken',
    wordmark: 'Freely Spoken',
    colors: {
      primary: '#172235',
      accent: '#B18A55',
      background: '#F7F1E8',
      surface: '#EFE4D3',
      softSurface: 'rgba(23,34,53,0.05)',
      text: '#111827',
      muted: '#6B6257',
      destructive: '#B94034',
      darkSurface: '#0F1724',
      inverseText: '#F7F1E8',
    },
  },
  dhammapada: {
    name: 'Idle Ashes',
    wordmark: 'idle ashes',
    colors: {
      primary: '#2B2A25',
      accent: '#C1784A',
      background: '#F4EEE6',
      surface: '#E9DFD2',
      softSurface: 'rgba(43,42,37,0.06)',
      text: '#24231F',
      muted: '#7C756B',
      destructive: '#B94034',
      darkSurface: '#181714',
      inverseText: '#F4EEE6',
    },
  },
  stoic: {
    name: 'Freely Spoken (Stoic)',
    wordmark: 'Freely Spoken',
    colors: {
      primary: '#172235',
      accent: '#B18A55',
      background: '#F7F1E8',
      surface: '#EFE4D3',
      softSurface: 'rgba(23,34,53,0.05)',
      text: '#111827',
      muted: '#6B6257',
      destructive: '#B94034',
      darkSurface: '#0F1724',
      inverseText: '#F7F1E8',
    },
  },
};
```

Export:

```ts
export function getBrand(appVariant: string): BrandTokens {
  if (appVariant === 'dhammapada') return BRANDS.dhammapada;
  if (appVariant === 'stoic') return BRANDS.stoic;
  return BRANDS.christian;
}

export function getBrandName(appVariant: string): string {
  return getBrand(appVariant).name;
}

export const Brand = BRANDS.christian;
```

**Step 2: Keep global theme compatible**

Update `constants/theme.ts` to keep Freely Spoken as the default global theme, using the new token names:

```ts
const tintColorLight = Brand.colors.primary;
const tintColorDark = Brand.colors.accent;
```

Update references from `navy`, `gold`, `ivory`, `parchment`, and `ink` to the new palette keys.

**Step 3: Add tests**

Create `constants/__tests__/brand.test.ts`:

```ts
import { describe, expect, it } from 'vitest';

import { getBrand, getBrandName } from '../brand';

describe('variant brand tokens', () => {
  it('keeps Freely Spoken as the default brand', () => {
    expect(getBrandName('christian')).toBe('Freely Spoken');
    expect(getBrand('unknown').colors.primary).toBe('#172235');
  });

  it('returns Idle Ashes tokens for the dhammapada variant', () => {
    const brand = getBrand('dhammapada');
    expect(brand.name).toBe('Idle Ashes');
    expect(brand.wordmark).toBe('idle ashes');
    expect(brand.colors.background).toBe('#F4EEE6');
    expect(brand.colors.primary).toBe('#2B2A25');
  });
});
```

**Step 4: Run tests**

Run:

```bash
npm test -- constants/__tests__/brand.test.ts
```

Expected: the new brand tests pass.

**Step 5: Commit**

Run:

```bash
git add constants/brand.ts constants/theme.ts constants/__tests__/brand.test.ts
git commit -m "Add variant-aware brand tokens"
```

---

### Task 5: Restyle Home Screen With Idle Ashes Tokens

**Files:**
- Modify: `app/index.tsx`

**Step 1: Replace the module-level `brandColors` dependency**

Remove:

```ts
const brandColors = Brand.colors;
```

Import `getBrand`:

```ts
import { getBrand, getBrandName } from '@/constants/brand';
```

Inside `HomeScreen`, derive:

```ts
const brand = useMemo(() => getBrand(appVariant), [appVariant]);
const styles = useMemo(() => buildStyles(brand.colors), [brand.colors]);
```

Update the title:

```tsx
<ThemedText type="title" style={styles.title}>
  {brand.wordmark}
</ThemedText>
```

This intentionally renders `idle ashes` lowercase for Dhammapada while preserving `Freely Spoken` for Christian.

**Step 2: Pass styles to child components**

Because `styles` becomes local to `HomeScreen`, pass it to helper components that currently close over the module-level `styles` object:

```tsx
<RecordingLevelMeter inputLevel={inputLevel} styles={styles} />
<PrivateProcessingCue styles={styles} ... />
<PrivateSummaryReview styles={styles} ... />
<LookupResultBlock styles={styles} ... />
```

Add a type alias:

```ts
type HomeStyles = ReturnType<typeof buildStyles>;
```

Use `styles: HomeStyles` in helper component props.

**Step 3: Convert the stylesheet factory**

Replace:

```ts
const styles = StyleSheet.create({
```

with:

```ts
function buildStyles(colors: ReturnType<typeof getBrand>['colors']) {
  return StyleSheet.create({
```

and close with:

```ts
  });
}
```

Update color references:

```ts
recordButton: {
  borderColor: colors.surface,
},
recordDot: {
  backgroundColor: colors.destructive,
},
processingHalo: {
  backgroundColor: withAlpha(colors.accent, 0.12),
  borderColor: withAlpha(colors.accent, 0.24),
},
processingCore: {
  borderColor: colors.primary,
  borderTopColor: colors.accent,
},
findVerseButton: {
  backgroundColor: colors.primary,
},
findVerseText: {
  color: colors.inverseText,
},
```

Add a small helper near the top of `app/index.tsx`:

```ts
function withAlpha(hex: string, alpha: number): string {
  const normalized = hex.replace('#', '');
  if (normalized.length !== 6) return hex;
  const value = Math.round(alpha * 255).toString(16).padStart(2, '0');
  return `#${normalized}${value}`;
}
```

React Native accepts 8-digit hex on current iOS/Android. If lint or runtime complains, replace with the existing rgba strings for each variant.

**Step 4: Serif-forward passage text**

Import `Fonts`:

```ts
import { Fonts } from '@/constants/theme';
```

Update result text styles:

```ts
verseText: {
  fontFamily: Fonts?.serif,
  fontSize: 18,
  lineHeight: 28,
},
altVerseText: {
  fontFamily: Fonts?.serif,
  fontSize: 16,
  lineHeight: 24,
},
```

Keep button and metadata text system sans for readability.

**Step 5: Run typecheck**

Run:

```bash
npm run typecheck
```

Expected: no TypeScript errors. Fix prop typing errors before continuing.

**Step 6: Commit**

Run:

```bash
git add app/index.tsx
git commit -m "Style Idle Ashes app variant"
```

---

### Task 6: Update Documentation For Variant Release

**Files:**
- Modify: `README.md`
- Modify: `assets/brand/README.md`

**Step 1: Update brand README**

`assets/brand/README.md` should document both asset sets:

```md
## Idle Ashes

- Product name: Idle Ashes
- Mark: abstract cooling ash fragments with restrained ember point
- Voice: quiet, private, reflective, literate
- Palette: charcoal, ash gray, warm ivory, clay, copper ember

### Files

- `idle-ashes-mark.svg` / `idle-ashes-mark.png`
- `idle-ashes-wordmark.svg` / `idle-ashes-wordmark.png`
- `idle-ashes-lockup.svg` / `idle-ashes-lockup.png`
- Expo assets in `assets/images/idle-ashes-*`
```

**Step 2: Update README setup notes**

In `README.md`, add a short Idle Ashes build note near the existing variant/EAS section:

```md
For Idle Ashes TestFlight builds, use the `production-idleashes` profile. The build uses `com.htsh.idleashes`, the `idle-ashes` Expo slug, and the shared lookup backend at `https://verses.hitesh.nyc`.

Do not commit `EXPO_PUBLIC_LOOKUP_CLIENT_SECRET`; configure it locally or in EAS environment variables.
```

**Step 3: Commit**

Run:

```bash
git add README.md assets/brand/README.md
git commit -m "Document Idle Ashes release setup"
```

---

### Task 7: Validate Backend And Dhammapada Lookup

**Files:**
- Read: `.env`
- Read: `server/app/lookup/dhammapada.py`

**Step 1: Check backend health**

Run:

```bash
curl -sS https://verses.hitesh.nyc/healthz
```

Expected:

```json
{"ok":true}
```

**Step 2: Run a Dhammapada lookup smoke test**

Use the client secret from local `.env` without printing it:

```bash
SECRET=$(awk -F= '/^EXPO_PUBLIC_LOOKUP_CLIENT_SECRET/{print $2}' .env | xargs)
curl -sS -X POST https://verses.hitesh.nyc/lookup \
  -H 'Content-Type: application/json' \
  -H "X-Lookup-Client-Secret: $SECRET" \
  -d '{
    "appVariant": "dhammapada",
    "anonymizedText": "the person feels overwhelmed and wants a quieter way to respond",
    "sentiment": "negative",
    "emotions": ["anxiety", "frustration"],
    "confidence": 0.82
  }'
```

Expected: JSON response with `primary`, `alternates`, `provider`, `model`, and `crisisFlag`.

If the response is 401, stop and check the server `LOOKUP_CLIENT_SECRET` versus local `.env`. If the response is 502, inspect provider keys and logs before building TestFlight.

---

### Task 8: Create Or Link The Idle Ashes EAS Project

**Files:**
- Modify: `app.config.js`
- Read: `eas.json`

**Step 1: Confirm EAS login and current project**

Run:

```bash
npx eas whoami
npx eas project:info
```

Expected: logged in as an account with access to owner `arlodog`; existing project is Freely Spoken / `mic-check`.

**Step 2: Create/link the Idle Ashes project**

Run the EAS project initialization under the Dhammapada variant:

```bash
EXPO_PUBLIC_APP_VARIANT=dhammapada npx eas project:init --force
```

Expected: EAS creates or links an Expo project for owner `arlodog` and slug `idle-ashes`, and reports a project id.

If the command edits `app.json` with a new static `extra.eas.projectId`, move that new id into the Dhammapada variant in `app.config.js` and restore the Freely Spoken id as the default Christian project id.

**Step 3: Persist the Idle Ashes project id**

After project creation, set:

```js
const IDLE_ASHES_EAS_PROJECT_ID = 'new-id-from-eas';
```

Do not leave this dependent on a local-only environment variable once the project id is known. Project ids are not secrets.

**Step 4: Verify both project ids**

Run:

```bash
npx expo config --json > /tmp/freely-spoken-config.json
EXPO_PUBLIC_APP_VARIANT=dhammapada npx expo config --json > /tmp/idle-ashes-config.json
node -e "for (const f of ['/tmp/freely-spoken-config.json','/tmp/idle-ashes-config.json']) { const c=require(f); console.log(c.name, c.slug, c.extra.eas.projectId) }"
```

Expected:

```text
Freely Spoken mic-check 9af03ee3-2eae-4f5c-b0fe-60200c3bd29d
Idle Ashes idle-ashes <new-id-from-eas>
```

**Step 5: Commit**

Run:

```bash
git add app.config.js app.json
git commit -m "Link Idle Ashes EAS project"
```

If `app.json` did not change, omit it from `git add`.

---

### Task 9: Full Local Verification

**Files:**
- All touched files

**Step 1: Run JavaScript checks**

Run:

```bash
npm test
npm run typecheck
npm run lint
```

Expected: all pass. If lint has pre-existing unrelated failures, document exact failures before moving on.

**Step 2: Verify Expo config again**

Run:

```bash
EXPO_PUBLIC_APP_VARIANT=dhammapada EXPO_PUBLIC_LOOKUP_API_URL=https://verses.hitesh.nyc npx expo config --json > /tmp/idle-ashes-config.json
node -e "const c=require('/tmp/idle-ashes-config.json'); console.log(JSON.stringify({name:c.name, slug:c.slug, icon:c.icon, bundle:c.ios.bundleIdentifier, scheme:c.scheme, lookup:c.extra.lookupApiUrl, variant:c.extra.appVariant, splash:c.plugins.find(p => Array.isArray(p) && p[0] === 'expo-splash-screen')?.[1]?.image}, null, 2))"
```

Expected JSON:

```json
{
  "name": "Idle Ashes",
  "slug": "idle-ashes",
  "icon": "./assets/images/idle-ashes-icon.png",
  "bundle": "com.htsh.idleashes",
  "scheme": "idleashes",
  "lookup": "https://verses.hitesh.nyc",
  "variant": "dhammapada",
  "splash": "./assets/images/idle-ashes-splash-icon.png"
}
```

**Step 3: Commit fixes if needed**

If validation required changes, commit them:

```bash
git add <changed-files>
git commit -m "Fix Idle Ashes validation issues"
```

---

### Task 10: Build And Submit Internal TestFlight

**Files:**
- Read: `eas.json`
- Read: `.env`

**Step 1: Configure EAS environment**

Ensure the Idle Ashes EAS project has:

```text
EXPO_PUBLIC_LOOKUP_CLIENT_SECRET=<current shared lookup client secret>
```

Use EAS environment management rather than committing the value to `eas.json`.

**Step 2: Create or verify App Store Connect app**

In App Store Connect, create an iOS app:

```text
Name: Idle Ashes
Bundle ID: com.htsh.idleashes
SKU: idle-ashes
Primary language: English
```

If EAS prompts to create bundle identifiers/credentials, allow it to manage credentials unless there is an existing Apple signing setup to reuse.

**Step 3: Queue production iOS build**

Run:

```bash
npx eas build --platform ios --profile production-idleashes
```

Expected: EAS queues and completes an iOS store build for `com.htsh.idleashes`.

**Step 4: Submit to App Store Connect**

Run:

```bash
npx eas submit --platform ios --profile production-idleashes
```

Expected: the latest Idle Ashes build uploads to App Store Connect.

**Step 5: Internal TestFlight setup**

In App Store Connect:

1. Open Idle Ashes.
2. Go to TestFlight.
3. Wait for build processing.
4. Complete export compliance if prompted. The app config sets `ITSAppUsesNonExemptEncryption` to false.
5. Add an internal testing group.
6. Add the build to the group.
7. Invite internal testers.

**Step 6: Device smoke test**

On a real supported iOS device:

1. Install Idle Ashes from TestFlight.
2. Confirm it installs beside Freely Spoken.
3. Confirm icon and splash are Idle Ashes.
4. Confirm permission prompts say Idle Ashes.
5. Record a short reflection.
6. Confirm transcription and anonymized summary review.
7. Submit lookup.
8. Confirm returned passage is a Dhammapada passage.
9. Confirm no debug link appears in the release build.

**Step 7: Final commit if release metadata changed**

If version/build metadata changed in source:

```bash
git add app.json eas.json app.config.js
git commit -m "Prepare Idle Ashes TestFlight build"
```

---

### Task 11: Final Handoff

**Files:**
- Read: `git log --oneline -5`
- Read: `git status --short`

**Step 1: Confirm repository state**

Run:

```bash
git status --short
git log --oneline -5
```

Expected: clean worktree and visible commits for assets, identity, tokens, styling, docs, EAS linkage, and release prep.

**Step 2: Summarize outcome**

Report:

- Branch name
- Commits created
- Backend health result
- Dhammapada smoke lookup result
- EAS project id for Idle Ashes
- EAS build URL/status
- App Store Connect/TestFlight status
- Any manual follow-up remaining
