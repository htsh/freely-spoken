# Other Wisdom Source Candidates

## Purpose

Capture candidate public-domain or public-domain-likely source material for future app variants beyond the committed Christian (v1) and Stoic (v2) directions.

The use case is: a user says something stressful, the app returns something useful, grounded, and source-backed. The app should not behave like a therapist, self-help coach, or generic advice bot.

## Version ordering (decided 2026-05-13)

1. **Christian (v1)** — first commit. Verse-shaped, largest audience, cleanest fetch story (Bible API).
2. **Stoic (v2)** — second commit. See `docs/stoic-curation-rubric.md` for the "Stoic but not bro-Stoic" content rules that govern catalog curation and response framing.
3. **Open slot (v3)** — Zen koans are no longer the committed v3. The slot will be filled by whichever corpus best matches the v1/v2 product shape and passes the criterion below.

## Provisional form-factor criterion

Both committed versions deliver **short, concrete passages** on stress-relevant themes. This is the implicit product shape but has not been validated against real users yet — treat it as a provisional filter for v3 candidates, not a hard rule. Revisit after v1 ships and there is something to hold in hand.

## Reusable Architecture Pattern

Use the same selection-and-fetch pattern across all versions:

1. User speaks into the microphone.
2. App transcribes on-device.
3. App runs sentiment extraction and anonymization on-device.
4. App sends only anonymized text and safe emotional metadata to backend lookup.
5. LLM selects a source-backed passage ID from a controlled catalog.
6. Backend fetches canonical text from the approved corpus (API for Christian, stored catalog for Stoic+).
7. App renders the canonical text plus a short reason or framing note.

Do not let the LLM author canonical wisdom text. The LLM should select and explain; the backend should fetch.

## v3+ Candidate Sources

Ranked by fit with the (provisional) concrete-short-passage criterion.

### Dhammapada — strongest v3 candidate by criterion

423 short verse-form sayings. Aphoristic in form, often a single image or instruction per verse.

Best for:

- Anger
- Craving
- Grief
- Mindfulness
- Speech
- Reactivity
- Conduct

Product fit:

- Excellent. Short, concrete, directly stress-relevant.
- Buddhist, but not specifically Zen — label clearly to avoid confusion if Zen later joins.
- More direct than koans; fits the v1/v2 shape almost perfectly.

Risks:

- Some verses may sound moralizing if matched poorly to user state.
- Translation choice affects tone substantially.

Candidate source:

- Project Gutenberg text: `https://www.gutenberg.org/files/2017/2017-h/2017-h.htm`

### Tao Te Ching

81 short aphoristic chapters. Many are usable as standalone passages.

Best for:

- Control
- Striving
- Conflict
- Over-effort
- Humility
- Non-reactivity
- Letting things unfold

Product fit:

- Strong. Aphoristic chapters fit the criterion well.
- Useful when the app should offer spaciousness rather than a concrete action plan.

Risks:

- Translations vary substantially; some are quite cryptic.
- Must choose known public-domain translations and track translator/provenance.

Candidate source:

- Wikisource translations index: `https://en.wikisource.org/wiki/Tao_Te_Ching`

### Pirkei Avot

Terse Jewish wisdom across ~6 chapters. Mishnaic sayings on conduct, speech, ego, attention.

Best for:

- Speech and restraint
- Ego and pride
- Conduct in conflict
- Patience

Product fit:

- Strong. Many sayings are one or two sentences and stand alone.

Risks:

- Theologically specific (Jewish context); needs clear labeling if mixed with other traditions.
- Translation/edition rights need confirmation per source.

Candidate source:

- Public-domain translations exist (e.g. Charles Taylor 1877). Verify per-edition before use.

### Confucian Analects

Short sayings, usually one to three sentences each.

Best for:

- Conduct
- Speech
- Restraint
- Learning posture
- Interpersonal calibration

Product fit:

- Strong. The form is naturally aphoristic.

Risks:

- Some sayings feel culturally distant without framing.
- Translation choice matters (Legge is public domain but Victorian in tone).

Candidate source:

- James Legge translation on Project Gutenberg.

### Bhagavad Gita

Mixed-length verses, often longer than the criterion prefers. Some short verses qualify.

Product fit:

- Likely its own future version rather than a v3 slot — theologically heavy and the form is more discursive than aphoristic.

Risks:

- Translation choice matters substantially.
- Could feel inappropriate if blended casually with other traditions.

Candidate source:

- Edwin Arnold translation on Project Gutenberg: `https://www.gutenberg.org/files/2388/2388-h/2388-h.htm`

## Reshape-required candidates

### Zen — deferred, koan form does not match the criterion

The original Zen plan (`docs/plans/2026-05-13-zen-koan-lookup.md`) used Gateless Gate koans. Koans are designed to *not* be concrete; they resist the aphorism form the first two versions are pulling toward.

If Zen ships, it likely needs a different content form than koans:

- **Zen sayings** — terse attributed statements from the masters
- **Dōgen excerpts** — selected short passages from *Shōbōgenzō* or *Genjō Kōan*
- **Hagakure-style terse passages** — different lineage but similar form factor

A v3 Zen would need a separate plan; the koan plan is preserved for reference only.

## Excluded by criterion

### Aesop's Fables

Story + moral form. Does not match the short-aphorism criterion. Could work in a future "parable" mode if the product shape changes.

### The Book of Tea

Essay-shaped, not aphorism-shaped. Selection would require heavy excerpting that breaks the source's structure.

## Suggested Taxonomy

If these sources become a broader wisdom backend, catalog items should include:

- `id`
- `tradition`
- `source`
- `title`
- `passageRef`
- `text`
- `translator`
- `sourceUrl`
- `publicDomainStatus`
- `licenseNote`
- `themes`
- `useWhen`
- `avoidWhen`
- `tone`
- `displayLabel`
- `summary`

Potential `tradition` values:

- `christian`
- `stoic`
- `buddhist`
- `tao`
- `jewish`
- `confucian`
- `zen` (if reshaped)
- `hindu`

## Rights and Provenance Rule

Ancient source material may be public domain, but translations, compilations, introductions, notes, formatting, and editorial selections may have separate copyright.

Before adding any source to app output:

1. Verify the exact translation/edition is public domain in the intended jurisdiction or explicitly licensed for reuse.
2. Store source URL, translator, publication date when known, and license note.
3. Keep commentary/interpretation separate from canonical source text.
4. Do not use random copied web text as canonical app content without provenance review.
