# Anonymized Sentiment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an on-device anonymized version of each transcript to the sentiment workflow and debug tooling.

**Architecture:** Extend the existing `useSentimentAnalyzer()` structured model result with `anonymizedText`. Keep the existing object-first/text-fallback strategy, normalize the new field defensively, and display it in both the main results flow and `/debug`.

**Tech Stack:** Expo Router, React Native, TypeScript, `@ratley/react-native-apple-foundation-models`, Swift FoundationModels CLI.

---

### Task 1: Extend Sentiment Result Contract

**Files:**
- Modify: `hooks/use-sentiment-analyzer.ts`

**Step 1: Add anonymized text to raw and normalized types**

Add `anonymizedText?: unknown` to `RawSentimentResult` and `anonymizedText: string` to `SentimentResult`.

**Step 2: Extend schema and prompt**

Add `anonymizedText` as a required string property in `SENTIMENT_SCHEMA`. Update `SENTIMENT_PROMPT` to require a privacy-preserving rewrite that keeps emotional gist while removing identifying specifics.

**Step 3: Normalize anonymized text**

Add `normalizeAnonymizedText(value)` that returns a trimmed model string when present, otherwise a conservative generic fallback.

**Step 4: Wire both model paths**

Include `anonymizedText` when setting result from `generateObject()` and from `parseStructuredSentiment()`.

### Task 2: Display Anonymous Version in the App

**Files:**
- Modify: `app/index.tsx`

**Step 1: Add results UI**

Under the existing emotions block, render `Anonymous version` and `sentimentResult.anonymizedText`.

**Step 2: Add focused styles**

Reuse existing typography and spacing with a small dedicated style for the anonymous text block.

### Task 3: Update Debug Screen

**Files:**
- Modify: `app/debug.tsx`

**Step 1: Update debug copy and title**

Make the debug screen describe sentiment plus anonymization.

**Step 2: Add privacy-heavy fixtures**

Replace or expand fixtures with examples containing names, organizations, locations, dates, ages, and medical details.

**Step 3: Display anonymized output**

Show `anonymizedText` in the normalized result block before raw model output.

### Task 4: Keep Swift CLI in Sync

**Files:**
- Modify: `tools/sentiment-cli/Sources/sentiment-cli/main.swift`
- Modify: `tools/sentiment-cli/README.md`

**Step 1: Add schema field**

Add `anonymizedText: String` to the `Sentiment` `@Generable` struct.

**Step 2: Update prompt**

Mirror the TypeScript prompt's anonymization requirement.

**Step 3: Update CLI README examples**

Mention that output now includes anonymized text.

### Task 5: Update Documentation

**Files:**
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `README.md`
- Modify: `docs/debug-testing.md`

**Step 1: Update behavior descriptions**

Mention that sentiment analysis now also produces anonymized text.

**Step 2: Update testing guidance**

Add anonymization success criteria and fixtures to the debug workflow.

### Task 6: Verify

**Commands:**

```bash
npm run lint
```

Expected: command exits successfully with no lint errors.

Manual checks still require Apple Intelligence-capable hardware:

```bash
cd tools/sentiment-cli
swift run sentiment-cli --raw "My name is Maya, I work at Northstar Clinic in Denver, and after my surgery on March 3 I feel scared and angry."
```

Expected: structured output includes an anonymized version that keeps fear/anger and a medical-workplace concern while removing the name, employer, city, and exact date.
