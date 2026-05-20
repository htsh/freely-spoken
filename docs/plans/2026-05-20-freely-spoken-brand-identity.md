# Freely Spoken Brand Identity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build and wire a production-ready Freely Spoken identity set for the Expo iOS app.

**Architecture:** Generate deterministic vector-derived assets from one repeatable source script, then point Expo metadata and theme tokens at the new identity. Keep user-facing brand changes separate from technical package identifiers to avoid accidental native migration work.

**Tech Stack:** Expo, React Native, TypeScript, Swift/CoreGraphics asset generation, PNG/SVG assets.

---

### Task 1: Add Repeatable Brand Asset Generation

**Files:**
- Create: `tools/branding/generate-freely-spoken-assets.swift`
- Create: `assets/brand/freely-spoken-mark.svg`
- Create: `assets/brand/freely-spoken-wordmark.svg`
- Create: `assets/brand/freely-spoken-lockup.svg`
- Create: `assets/brand/README.md`
- Modify: `assets/images/icon.png`
- Modify: `assets/images/splash-icon.png`
- Modify: `assets/images/favicon.png`
- Modify: `assets/images/android-icon-background.png`
- Modify: `assets/images/android-icon-foreground.png`
- Modify: `assets/images/android-icon-monochrome.png`

**Step 1: Implement the generator**

Create a Swift script that draws the app icon, splash lockup, standalone mark PNGs, Android adaptive assets, favicon, and SVG source files from shared geometry and color constants.

**Step 2: Run the generator**

Run: `swift tools/branding/generate-freely-spoken-assets.swift`

Expected: all PNG and SVG files listed above are created or regenerated.

**Step 3: Verify dimensions**

Run: `file assets/images/icon.png assets/images/splash-icon.png assets/images/favicon.png assets/images/android-icon-foreground.png assets/images/android-icon-background.png assets/images/android-icon-monochrome.png`

Expected: icon and splash are 1024x1024, favicon is 48x48, Android foreground/background are 512x512, Android monochrome is 432x432.

### Task 2: Wire Brand Metadata And Theme Tokens

**Files:**
- Create: `constants/brand.ts`
- Modify: `constants/theme.ts`
- Modify: `app.json`
- Modify: `app/index.tsx`

**Step 1: Add brand constants**

Create `constants/brand.ts` with the product name and shared color palette.

**Step 2: Update theme tokens**

Use the brand colors in `constants/theme.ts` for text, backgrounds, tints, and icon colors.

**Step 3: Update user-facing app metadata**

Change Expo display name and permission copy to `Freely Spoken`. Keep slug, scheme, owner, package, and bundle identifier unchanged.

**Step 4: Update home-screen brand and UI colors**

Change the title to `Freely Spoken` and replace ad hoc blue/gray UI colors with brand tokens where they are part of the brand surface.

### Task 3: Verify

**Files:**
- Read: generated assets
- Read: TypeScript and JSON changes

**Step 1: Lint**

Run: `npm run lint`

Expected: PASS.

**Step 2: Inspect generated assets**

Open the app icon and splash image locally to confirm the mark, wordmark, and contrast are usable.
