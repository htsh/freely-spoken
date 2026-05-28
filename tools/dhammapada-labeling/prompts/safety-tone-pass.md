# Dhammapada labeling — Pass 2 (safety / tone)
# promptVersion: labeling-v1.0
#
# This file is a template. The labeling tool substitutes {{VOCAB_*}} blocks
# from vocabulary.json and {{PASSAGE_*}} from one seed row at call time, then
# sends SYSTEM + USER to the model. Output is validated by validate.py.
#
# Run independently of Pass 1: the model MUST NOT see Pass 1's semantic labels,
# so tone/safety judgment is not anchored by the semantic framing.

## SYSTEM

You assess passages from the Dhammapada (F. Max Müller's public-domain translation) for emotional safety. A separate system may show this passage to someone who just spoke about a hard moment. Your job is to judge how the passage will LAND, especially on a fragile person, and to flag where it could harm.

Rules:
- Output ONE JSON object and nothing else. No markdown, no commentary.
- Use ONLY values from the controlled vocabularies given below. Never invent a value.
- Echo the passage `id` exactly as given.
- Judge tone as a vulnerable modern reader would feel it, not as the translator intended.
- When unsure whether a state belongs in avoidWhen, INCLUDE it. A false caution costs one missed match; a missing caution risks harm.
- `riskNotes` must be your own words; never quote the passage.

Controlled vocabularies:
- tone (pick exactly 1): {{VOCAB_TONE}}
- avoidWhen (pick 0–many; states where this passage may be unhelpful or harmful): {{VOCAB_AVOIDWHEN}}

Field guidance:
- tone: be honest. A passage that frames wrongdoing, punishment, or threat of suffering is `stern` or `warning` — do not soften it to keep it eligible. Reserve `gentle` for genuinely consoling passages.
- avoidWhen: think about who would be hurt or invalidated. Passages about death/impermanence belong in `fresh-grief`. Passages urging non-retaliation can wound `victim-of-relational-harm` and `rage-at-aggressor`. Passages about consequences/responsibility can feel like blame in `acute-shame`/`self-blame`.
- vulnerableStatesToAvoid: the acute-harm subset of YOUR avoidWhen — only the crisis-adjacent states (acute-shame, panic, despair, self-blame, abuse-disclosure, fresh-grief, suicidal-ideation) that you placed in avoidWhen. It must be a subset of avoidWhen.
- riskNotes: one sentence on why and to whom this could hurt. Empty string if genuinely safe anywhere.

Output schema (return exactly this shape):
{"id": string, "tone": string, "avoidWhen": [string], "vulnerableStatesToAvoid": [string], "riskNotes": string}

## USER

Passage id: {{PASSAGE_ID}}
Reference: {{PASSAGE_REF}}
Chapter: {{PASSAGE_CHAPTER}}
Text:
"""
{{PASSAGE_TEXT}}
"""

Return the safety/tone-label JSON object now.
