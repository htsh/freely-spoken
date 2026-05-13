# Hosted Response Lookup Brainstorm Notes (2026-05-11)

## Purpose

Capture product ideas for the next phase so they do not get lost before implementation.

## Direction

- Keep a tight one-shot loop: user speaks once, app returns one relevant response.
- Preserve privacy posture: hosted providers receive anonymized text only.
- Keep this product non-conversational (not chat, no session memory).
- Update the product direction from one Christian-only experience to two related versions: Christian and Zen.
- Christian version returns Christian scripture-oriented guidance.
- Zen version returns Zen-oriented reflection/practice guidance.
- Treat Christian and Zen as the active scope. Do not broaden to a generic multi-tradition product until a later decision explicitly changes that.
- Use the hosted LLM for relevance/reference selection, not as the canonical source text author.
- Fetch canonical Christian verse text from a Bible API after the LLM selects a verse.
- Fetch canonical Zen koan text from a koan collection after the LLM selects a koan/reference.
- Consider reading the fetched verse or koan aloud to the user.

## Ideas To Carry Forward

1. Add a compact intent tag from on-device analysis (`comfort`, `guidance`, `gratitude`, `fear`, `conflict`) and pass it into hosted lookup prompts to improve relevance.
2. Keep hosted selection strictly structured for deterministic rendering and validation. Christian can use `{ reference, shortReason }`; Zen needs a separate koan identifier/reference decision.
3. Introduce a provider adapter abstraction now (`lookupSpiritualResponse(input): SpiritualResponseResult`) so provider changes do not affect UI/state machine code.
4. Add a small cooldown cache keyed by anonymized-text hash to reduce duplicate provider calls during rate-limit windows.
5. Prepare for two product variants using a small version boundary (`christian` and `zen`) while preserving one-shot UX and shared privacy infrastructure.
6. Add a canonical-content boundary after LLM selection: Bible API for Christian, koan collection for Zen.
7. Treat read-aloud as a shared optional capability that consumes fetched canonical text.

## Two-Version Notes

- Shared pipeline: recording, transcription, sentiment analysis, anonymization, hosted provider safety, bounded retries, and debug metadata.
- Christian-specific layer: Bible API source, verse-reference prompt language, response copy, and visual tone for scripture-oriented guidance.
- Zen-specific layer: koan collection source, koan-reference prompt language, response copy, and visual tone for Zen reflection or practice.
- Details such as app naming, branding, exact response format, and corpus strategy are intentionally deferred.

## Zen Koan Source Candidates

- Terebess Asia Online:
  - `https://terebess.hu/zen/`
  - `https://terebess.hu/english/gateless.html`
  - `https://terebess.hu/zen/blue.html`
  - `https://terebess.hu/english/101.html`
- Internet Sacred Text Archive:
  - `https://sacred-texts.com/bud/zen/index.htm`
  - `https://sacred-texts.com/bud/glg/index.htm`
- Wikisource:
  - `https://en.wikisource.org/wiki/The_Gateless_Gate`
- GitHub seed data:
  - Search `"zen koans dataset"` or `"101 zen stories json"` for machine-readable public-domain koan compilations.
- AshidaKim 101 Zen Koans index:
  - `https://ashidakim.com/zenkoans/zenindex.html`

Before implementation, verify licensing, translation provenance, stable identifiers, and whether the source supports app redistribution/display. Prefer sources that can map cleanly from an LLM-selected koan/reference to deterministic fetched text.

## Product Guardrails

- Do not return raw provider prose to UI when schema parse fails; fail clearly and retry/fallback.
- Do not leak raw transcript beyond on-device pipeline.
- Do not display provider-generated Bible verse text or koan text as canonical content.
- Keep retry behavior bounded to avoid long wait times and cost surprises.
