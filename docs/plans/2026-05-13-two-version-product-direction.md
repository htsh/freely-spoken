# Two-Version Product Direction (2026-05-13)

## Purpose

Capture the current product direction before implementation details are settled.

## Direction

mic-check should evolve into two related iOS app versions:

1. **Christian version** — keeps the one-shot spiritual response loop oriented around Christian scripture and pastoral-style guidance.
2. **Zen version** — uses the same privacy-first listening and anonymization pipeline, but orients the response around Zen framing, reflection, and practice rather than Bible verses.

The details of naming, branding, content sources, tone, and distribution are intentionally undecided. Future specs should resolve those details before implementation.

## Retrieval Pattern

Both versions should use the same selection-and-fetch pattern:

1. The hosted LLM receives anonymized context and selects the best canonical reference.
2. The app fetches the actual canonical text from a trusted source.
3. The app renders the fetched text, not provider-generated scripture or koan text.

For the Christian version, the trusted source is a Bible API. The LLM should identify the verse reference, then the app should fetch the verse text from that API.

For the Zen version, the trusted source is a koan collection. The LLM should identify the koan or collection reference, then the app should fetch the koan text from that collection.

This reduces hallucinated source text and keeps the LLM responsible for matching/relevance rather than canonical content.

## Zen Source Candidates

Potential free sources for the Zen-side koan collection:

- **Terebess Asia Online (TAO)** — strong candidate for research and comparison because it collects many Zen texts and often includes multiple translations.
  - Main Zen index: `https://terebess.hu/zen/`
  - The Gateless Gate / Mumonkan: `https://terebess.hu/english/gateless.html`
  - The Blue Cliff Record / Hekiganroku: `https://terebess.hu/zen/blue.html`
  - 101 Zen Stories: `https://terebess.hu/english/101.html`
- **Internet Sacred Text Archive** — useful for older public-domain translations and plain HTML source material.
  - Zen Buddhism index: `https://sacred-texts.com/bud/zen/index.htm`
  - The Gateless Gate, Nyogen Senzaki translation: `https://sacred-texts.com/bud/glg/index.htm`
  - Planned primary source for Gateless Gate canonical text and occasional interpretation/commentary, with interpretation kept separate from koan text.
- **Wikisource** — useful when the text/license status is clearly public domain or compatible with reuse.
  - The Gateless Gate: `https://en.wikisource.org/wiki/The_Gateless_Gate`
- **GitHub datasets** — possible developer-friendly seed data if license and provenance are clean.
  - Search terms: `"zen koans dataset"`, `"101 zen stories json"`
- **AshidaKim 101 Zen Koans index** — possible reference/source candidate for the `101 Zen Stories` corpus, pending license and provenance review.
  - `https://ashidakim.com/zenkoans/zenindex.html`

Treat these as candidates, not final implementation choices. Before bundling, caching, or fetching koan text from any source, verify license, translation provenance, text structure, and whether the app can legally redistribute or display the content.

## Shared Product Spine

Both versions should preserve the core interaction model:

1. User speaks once.
2. Audio is transcribed on-device.
3. Sentiment/emotional context and anonymized text are produced on-device.
4. Only anonymized text may leave the device for hosted inference or retrieval.
5. The app returns one focused response, not a chat thread.
6. The app may optionally read the verse or koan aloud to the user.

## Version-Specific Surface Area

Keep shared infrastructure separate from version-specific behavior.

Shared infrastructure should include:

- Recording and on-device transcription
- On-device sentiment/emotion extraction
- On-device anonymization and privacy guardrails
- Hosted request safety rules
- Canonical content fetch after LLM reference selection
- Optional read-aloud playback path
- Retry/fallback provider mechanics
- Debug metadata and manual testing paths

Version-specific behavior should include:

- Content source or retrieval target
- Prompt tone and response schema
- Result screen language
- Branding, iconography, and visual direction
- Any tradition-specific safety or theological/philosophical constraints

## Planning Implications

- Do not hard-code the product as Christian-only in new architecture.
- Do not generalize prematurely into many traditions. The active direction is exactly two versions: Christian and Zen.
- Prefer a small `appVariant` or equivalent boundary over scattering conditional logic through UI and hooks.
- Keep the first implementation one-shot. Avoid chat, memory, accounts, feeds, or persistent history unless a future spec explicitly changes that.
- Continue treating raw transcript and audio as local-only data.
- Do not let the hosted LLM author canonical verse or koan text. It should select a reference; the app should fetch the source text.

## Open Questions For Future Specs

1. Whether the two versions are separate app targets/bundles or a single app with a variant switch during development.
2. Which Bible API to use and which translation(s) are allowed.
3. What koan collection to use, how koans are identified, and which source/license is acceptable.
4. What each version returns around the canonical text: source text only, source text plus short reflection, source text plus practice prompt, or another shape.
5. Whether read-aloud is automatic, user-triggered, or omitted from the first implementation.
6. How each version should handle sensitive mental-health or crisis language.
