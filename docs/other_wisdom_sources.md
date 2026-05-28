# Other Wisdom Source Candidates — decision sheet

Compact, ranked-by-criterion shortlist for wisdom corpora beyond v3. The longer per-source notes live in `docs/other_sources.md`; this file tracks v4+ candidates now that v3 is committed.

## Ordering as of 2026-05-28

1. **Christian** — v1, committed.
2. **Stoic** — v2, committed. See `docs/stoic-curation-rubric.md` for the "Stoic but not bro-Stoic" content rules.
3. **Dhammapada** — v3, committed. 423 short verse-form sayings. Buddhist (not Zen — label clearly). In-flight plan: `openspec/changes/dhammapada-catalog-lookup/`.
4. **Open slot (v4)** — fills with whichever remaining corpus best matches the v1/v2/v3 product shape and passes rights review.

## Provisional criterion

v4+ candidates evaluated against: *"delivers short, concrete passages on stress-relevant themes."*

v1, v2, and v3 are all aphorism-shaped. The criterion fell out of that — it is not yet validated against real user experience. Treat as a strong default; revisit after v1 ships and there's something in hand.

## v4+ shortlist (ranked by criterion fit)

1. **Tao Te Ching** — 81 short aphoristic chapters. Control, striving, non-reactivity. Translation provenance matters; use known public-domain (Legge, Goddard).
2. **Pirkei Avot** — terse Jewish wisdom across ~6 chapters. Speech, ego, conduct. Public-domain translations exist.
3. **Confucian Analects** — short sayings. Conduct, speech, restraint. Legge translation public domain.

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
