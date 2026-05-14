# Other Wisdom Source Candidates — decision sheet

Compact, ranked-by-criterion shortlist for v3+ wisdom corpora. The longer per-source notes live in `docs/other_sources.md`; this file is the decision sheet for which corpus fills the v3 slot.

## Ordering as of 2026-05-13

1. **Christian** — v1, committed.
2. **Stoic** — v2, committed. See `docs/stoic-curation-rubric.md` for the "Stoic but not bro-Stoic" content rules.
3. **Open slot (v3)** — Zen koans no longer the committed v3. Slot fills with whichever corpus best matches the v1/v2 product shape and passes rights review.

## Provisional criterion

v3+ candidates evaluated against: *"delivers short, concrete passages on stress-relevant themes."*

Both v1 and v2 are aphorism-shaped. The criterion fell out of that — it is not yet validated against real user experience. Treat as a strong default; revisit after v1 ships and there's something in hand.

## v3+ shortlist (ranked by criterion fit)

1. **Dhammapada** — 423 short verse-form sayings. Anger, craving, grief, speech, mindfulness. Buddhist (not Zen — label clearly). Project Gutenberg text public domain.
2. **Tao Te Ching** — 81 short aphoristic chapters. Control, striving, non-reactivity. Translation provenance matters; use known public-domain (Legge, Goddard).
3. **Pirkei Avot** — terse Jewish wisdom across ~6 chapters. Speech, ego, conduct. Public-domain translations exist.
4. **Confucian Analects** — short sayings. Conduct, speech, restraint. Legge translation public domain.

## Reshape-required candidates

- **Zen** — koans don't fit the criterion by design. Could ship if reshaped (Zen sayings, Dōgen *Shōbōgenzō* excerpts, Hagakure-style terse passages). The koan plan in `docs/plans/2026-05-13-zen-koan-lookup.md` is preserved for reference only, not as the active v3 plan.
- **Bhagavad Gita** — some short verses qualify; theologically heavy, probably its own version rather than a v3 slot.

## Excluded by criterion

- **Aesop's Fables** — story-shaped, not aphorism-shaped.
- **Book of Tea** — essay-shaped.

## Rights rule

Ancient text may be public domain but translations/compilations may not be. Before adding any source:

1. Verify exact translation/edition is public domain or explicitly licensed for reuse.
2. Store: source URL, translator, publication date, license note.
3. Keep commentary/interpretation separate from canonical source text.

## Catalog schema (if backend expands)

`id, tradition, source, title, passageRef, text, translator, sourceUrl, publicDomainStatus, licenseNote, themes, useWhen, avoidWhen, tone, displayLabel, summary`
