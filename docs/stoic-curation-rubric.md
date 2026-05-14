# Stoic Curation Rubric — "Stoic but not bro-Stoic"

**Status:** Draft. Captured while thinking is fresh. Revisit before Stoic v2 implementation begins. Not yet validated against real catalog or user feedback.

## Why this doc exists

Stoicism in 2026 is having a cultural moment with young men, which is a real product tailwind. But the filtered version circulating online — "be unbothered, dominate, sigma mindset, grind, repress emotion" — is not what the texts actually say. The Stoic v2 app needs to serve **the version of Stoicism the texts actually are, for the audience drawn to what the filtered version pretends to be.**

This rubric governs three things:

1. **Catalog curation** — which passages enter the Stoic corpus.
2. **Response framing** — how the LLM's `shortReason` and any companion copy are written.
3. **Translation choice** — Victorian-era translations can read as severe in ways modern users misread.

If a contributor only reads one section, read **Include criteria** and **Exclude criteria** below.

## What Stoicism actually centers

For grounding, the actual content the catalog should be drawn from:

- The dichotomy of control: what's up to us vs what isn't.
- Attention as a practice — returning to the present, noticing what is actually here.
- Emotion as data: notice, name, examine, don't suppress.
- Impermanence and mortality as humbling perspective.
- Disposition toward externals: indifferent to fortune, not contemptuous of others.
- Practical exercises: the view from above, premeditation of adversity, evening review.

## Include criteria

A passage is a candidate for the catalog if it does **at least one** of the following:

- Acknowledges difficulty rather than dismissing it.
- Frames agency without demanding domination ("what is yours to do" rather than "crush this").
- Names emotion as information, not as enemy.
- Addresses internal experience rather than interpersonal victory.
- Offers practical orientation toward attention or perception.
- Frames death or impermanence as humility, not as edge.
- Maps cleanly to a recognizable modern stressor (anxiety, anger, rejection, uncertainty, shame, control) without sounding clinical.

## Exclude criteria

A passage is **disqualified** if any of the following apply, even if it is technically Stoic:

- Reads as endorsing emotional suppression or "be unbothered."
- Frames the goal as domination, control of others, or social victory.
- Treats wealth, status, or productivity as virtue.
- Equates hardness with character.
- Could plausibly be misread as advice for "winning" at work or with women.
- Uses master/slave or owner/property metaphors that don't survive modern reading.
- Is severe or cold in a way that lands on a vulnerable user as cruel.
- Reads more like advice for ruling an empire than for a person at 11pm with a problem.

When in doubt, ask: *if a man in real distress read only this passage tonight, would it meet him or harden him?* Exclude anything that hardens.

## Response framing tone — do / don't

The LLM-generated `shortReason` and any companion copy should follow these rules.

### Avoid

- "You are stronger than this."
- "Real Stoics…"
- "Be unbothered."
- "Like a rock."
- "Dominate," "crush," "destroy," "sigma," "alpha," "winning."
- Any framing that positions the user against other people.
- Any framing that diagnoses the user or prescribes behavior clinically.
- Quoting Marcus Aurelius as if invoking a brand.

### Prefer

- "Notice…"
- "What's yours to do here."
- "Even Marcus, writing to himself, returned to this."
- Language of presence, attention, and proportion.
- Plain modern English. The passage carries the weight; the framing stays out of the way.
- Acknowledging the difficulty before offering the frame.

### Length

`shortReason` should be one to three short sentences. The canonical passage is the answer; the reason is a doorway, not a sermon.

## Translation considerations

Translation choice is itself a tonal lever. Same Marcus, very different feel:

- **George Long (1862)** — public domain, widely available, but Victorian rhythm can read as cold or severe to modern ears. Some passages land harshly that weren't harsh in Greek.
- **Meric Casaubon (1634)** — too archaic for modern use.
- **Higginson (Epictetus, 1865)** — more accessible than Long; reasonable default for Enchiridion.
- **Elizabeth Carter (Epictetus, 1758)** — public domain, careful, sometimes formal.

Practical guidance for v2:

- Prefer the most accessible public-domain translation per author.
- If a Long passage reads severe but the Greek isn't, prefer a different translation or exclude.
- Store `translator` and `sourceUrl` per passage so swaps are traceable.
- Do not silently modernize translations — that crosses into LLM-authored text territory, which the architecture forbids.

## Edge cases by source

### Marcus Aurelius, *Meditations*

- ✅ Passages on impermanence, returning to attention, the brevity of life, the smallness of grievance.
- ✅ Reminders to himself about patience with others' shortcomings.
- ⚠️ "Be like the rock the waves break against" — borderline. Excludable if the catalog already covers presence-under-difficulty without the hardness frame.
- ⚠️ Passages about ruling, empire, or one's "station" — exclude or carefully select; they read as elitist out of context.
- ❌ Anything that scans as Roman martial posture.

### Epictetus, *Enchiridion*

- ✅ The opening sections on what is up to us vs not — core, include.
- ✅ Passages on judgment as the source of disturbance.
- ✅ Practical exercises (the broken jug, the loved one, the journey).
- ⚠️ Master/slave language — Epictetus was formerly enslaved and used the metaphor critically, but it does not survive modern reading without context. Exclude or substitute.
- ⚠️ Passages about social roles — selective.

### Seneca (if added later)

- ✅ Letters on grief, anger, time, friendship.
- ⚠️ Letters on slavery — historically progressive for their time, but require modern framing to land. Probably exclude from v2.
- ⚠️ Wealth passages — Seneca was famously rich; some passages read as defensive. Selective.

## Sample sketches (illustrative, not catalog entries)

These are rough sketches of what a good entry might look like, to make the rubric concrete.

**Good fit — Epictetus, Enchiridion §5**

> Men are disturbed not by the things which happen, but by the opinions about the things.

Why included: directly addresses the core cognitive reframe. Concrete. Doesn't demand suppression — only reframes the locus of disturbance. Maps cleanly to anxiety, anger, rejection. Short.

Reason framing: "Notice where the disturbance is actually located."

**Good fit — Marcus, *Meditations* IV.3 (excerpt)**

> Men seek retreats for themselves, houses in the country, sea-shores, and mountains… But this is altogether a mark of the most common sort of men, for it is in thy power whenever thou shalt choose to retire into thyself.

Why included: practical, attention-oriented, addresses a common modern impulse without scolding it. The retreat-into-self framing is exactly the kind of concrete practice the app wants to surface.

Reason framing: "The retreat you want is closer than the trip you're planning."

**Borderline — Marcus, *Meditations* IV.49 (the rock passage)**

> Be like the promontory against which the waves continually break, but it stands firm and tames the fury of the water around it.

Why borderline: the metaphor is beautiful in context but pulls toward the "be a rock" reading that already saturates the cultural moment. The catalog probably doesn't need this — there are better passages for the same theme (returning to attention under stress) that don't risk the hardness reading.

Decision: exclude from v2 unless reframed by surrounding catalog.

## Open questions

1. Should the catalog include any Seneca, or stay v2 to Epictetus + Marcus only?
2. How is "crisis-language" handled — passages excluded entirely from selection when the anonymized text reads as crisis, or selection short-circuited to a resource card before reaching the LLM?
3. Is `shortReason` always LLM-authored, or do we author a small library of safe framings per passage and have the LLM pick one?
4. Read-aloud audio: if added, voice choice matters here. A wrong voice (commanding, masculine-coded, "Roman general") would undo a lot of this rubric's work.

## Status reminder

This is draft thinking. Until validated against a real catalog, real responses, and real user reactions, treat the criteria above as strong defaults rather than finished policy. Update this doc when the v2 catalog is curated and again after the first real-user feedback.
