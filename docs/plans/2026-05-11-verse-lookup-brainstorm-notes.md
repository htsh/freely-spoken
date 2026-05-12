# Verse Lookup Brainstorm Notes (2026-05-11)

## Purpose

Capture product ideas for the next phase so they do not get lost before implementation.

## Direction

- Keep a tight one-shot loop: user speaks once, app returns one relevant verse.
- Preserve privacy posture: hosted providers receive anonymized text only.
- Keep this product non-conversational (not chat, no session memory).

## Ideas To Carry Forward

1. Add a compact intent tag from on-device analysis (`comfort`, `guidance`, `gratitude`, `fear`, `conflict`) and pass it into verse lookup prompts to improve relevance.
2. Keep hosted response strictly structured as `{ reference, verseText, shortReason }` for deterministic rendering and validation.
3. Introduce a provider adapter abstraction now (`lookupVerse(input): VerseResult`) so provider changes do not affect UI/state machine code.
4. Add a small cooldown cache keyed by anonymized-text hash to reduce duplicate provider calls during rate-limit windows.
5. Prepare future multi-tradition support using a single `tradition` enum (`christian` now, with future `hindu`, `muslim`, `buddhist`) while preserving one-shot UX.

## Product Guardrails

- Do not return raw provider prose to UI when schema parse fails; fail clearly and retry/fallback.
- Do not leak raw transcript beyond on-device pipeline.
- Keep retry behavior bounded to avoid long wait times and cost surprises.
