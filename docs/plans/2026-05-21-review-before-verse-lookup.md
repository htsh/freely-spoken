# Review Before Verse Lookup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an explicit review step so users see the anonymized payload before sending it for verse lookup.

**Architecture:** Keep the existing hook pipeline. Change `app/index.tsx` so sentiment success enters a new `review` app state, then call `lookup()` only from a user action.

**Tech Stack:** Expo, React Native, TypeScript, existing hooks.

---

### Task 1: Update State Machine

**Files:**
- Modify: `app/index.tsx`

**Step 1: Add a review app state**

Extend `AppState` with `review`.

**Step 2: Stop automatic lookup**

Change the sentiment completion effect so `sentimentResult` sets `appState` to `review` instead of `responseLookup` and does not call `lookup()`.

**Step 3: Add submit handler**

Add a handler that builds the existing lookup request, sets `appState` to `responseLookup`, and calls `lookup(req)`.

### Task 2: Add Review and Processing UI

**Files:**
- Modify: `app/index.tsx`

**Step 1: Add processing cue component**

Render a branded privacy-processing cue for transcription/anonymization.

**Step 2: Add review screen**

Show the anonymized text, privacy explanation, and `Find My Verse` button.

**Step 3: Keep reset available**

Provide a secondary "Record Again" action on the review screen.

### Task 3: Verify

**Files:**
- Read: `app/index.tsx`

**Step 1: Lint**

Run: `npm run lint`

Expected: PASS.

**Step 2: Inspect diff**

Confirm no network lookup runs before the review CTA.
