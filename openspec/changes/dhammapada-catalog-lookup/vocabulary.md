## Controlled vocabularies for the Dhammapada catalog (task 2.4)

This document explains each axis in `vocabulary.json`, gives one-line glosses per value, and lays out the crisis-flag hard-exclusion rules.

Freeze rules:

- These vocabularies are the source of truth for labeling prompts (task 2.5), validation (task 2.7), the shortlist heuristic (task 4.4a), and the crisis-flag hard-exclusion list (task 4.6).
- No value is added, renamed, or removed without bumping the `version` in `vocabulary.json` and triggering a rubric review (task 2.9). Renaming a value is a relabeling event for every row that used it.
- The vocabulary is intentionally tight. The labeling rubric (task 2.4a) will instruct the labeler to pick the closest fit rather than expand.

## themes (27 values)

Catalog-content categories. What the verse is *about*. Pick 1–4 per row.

| Value | Gloss |
|---|---|
| `mind` | The mind itself, mental states, mental cultivation. |
| `thought` | Quality and direction of thinking; thinking shapes experience. |
| `speech` | What is said and how; speech as karma. |
| `conduct` | Bodily action, deeds, behavior. |
| `consequences` | Karma, results of action, sowing and reaping. |
| `anger` | Anger as an experience or as a force to be released. |
| `non-hatred` | Hatred set aside; non-retaliation; meeting hatred with non-hatred. |
| `ill-will` | Cultivated ill-will, malice, wish for harm. |
| `craving` | Tanha, grasping, thirst. |
| `attachment` | Clinging to people, possessions, outcomes. |
| `impermanence` | Anicca; everything passes. |
| `death` | Mortality, the inevitability of death. Crisis-flag hard-exclusion theme. |
| `mindfulness` | Heedfulness (appamāda), awareness as path. |
| `heedlessness` | Pamāda; carelessness, distraction. |
| `self-restraint` | Restraint of senses, speech, action. |
| `virtue` | Sīla; moral conduct as a foundation. |
| `wisdom` | Paññā; insight, discernment. |
| `ignorance` | Avijjā; not-seeing-clearly. |
| `companionship` | Choice of friends; who one walks with. |
| `the-wise` | The character and conduct of the wise person. |
| `the-fool` | The character and conduct of the fool. |
| `pride` | Conceit, self-importance. |
| `effort` | Energy, exertion, persistence on the path. |
| `peace` | Equanimity, stilling, rest. |
| `self-mastery` | Mastery over the self; self as one's own refuge. |
| `ascetic-discipline` | Renunciation, austerity, the homeless life. Crisis-flag hard-exclusion theme. |
| `moral-rebuke` | Stern correction, condemnation of wrongdoing. Crisis-flag hard-exclusion theme. |

## tone (9 values)

The felt tone the passage conveys. Pick exactly 1 per row.

| Value | Gloss | Crisis hard-exclude? |
|---|---|---|
| `gentle` | Kind, soft, consoling. | no |
| `direct` | Plainspoken, matter-of-fact, neither stern nor soft. | no |
| `contemplative` | Invites reflection without prescribing. | no |
| `reflective` | Looks back on a truth or pattern. | no |
| `affirming` | Names a positive quality and encourages it. | no |
| `aphoristic` | Compact proverb-style; neutral on warmth. | no |
| `exhortative` | Urges action or effort; firm but not condemning. | no |
| `stern` | Sharply corrective, blame-adjacent. | **yes** |
| `warning` | Frames consequence as threat; cautionary. | **yes** |

## useWhen (22 values)

User state or situation labels. When this passage is helpful. Pick 1–5 per row.

Aligned with sentiment + emotion labels the device can emit, plus richer situational labels for matching.

| Value | Gloss |
|---|---|
| `anger` | Active anger present. |
| `resentment` | Slow-burning anger held over time. |
| `reactivity` | Quick reaction without pause. |
| `speech-regret` | Recently said something they wish they hadn't. |
| `craving` | Wanting, grasping, urge. |
| `envy` | Wanting what someone else has. |
| `restlessness` | Can't settle; unease. |
| `worry` | Anxious looping about a future event. |
| `rumination` | Looping replay of a past event. |
| `conflict` | Active interpersonal conflict. |
| `relational-hurt` | Hurt within a relationship (not abuse — see `avoidWhen`). |
| `discouragement` | Loss of motivation on a path or effort. |
| `pride` | Conceit, ego, looking down on others. |
| `confusion` | Don't-know mind; uncertain what to do. |
| `doubt` | Wavering, second-guessing the path. |
| `gratitude` | Feeling thankful; wanting to honor that. |
| `contentment` | Sense of having enough. |
| `equanimity` | Settled, even, neither pulled nor pushed. |
| `joy` | Active joy or delight. |
| `patience-needed` | Situation calls for waiting through difficulty. |
| `generosity-impulse` | Impulse to give, share, let go. |
| `complacency` | Drifted into heedlessness; needs a wake-up nudge. |

## avoidWhen (9 values)

Vulnerable user states where this passage may harm. Pick 0–N per row.

| Value | Gloss | Crisis-adjacent? |
|---|---|---|
| `acute-shame` | Sharp present-tense shame about self. | **yes** |
| `panic` | Acute panic, dysregulated nervous system. | **yes** |
| `despair` | Sense that nothing will get better. | **yes** |
| `self-blame` | Active self-blame, especially for harm received. | **yes** |
| `abuse-disclosure` | User is describing being abused by another. | **yes** |
| `fresh-grief` | Recent bereavement, raw loss. | **yes** |
| `suicidal-ideation` | Active or recent suicidal thoughts. | **yes** |
| `rage-at-aggressor` | Anger at someone who harmed them; not the same as ordinary anger. | no |
| `victim-of-relational-harm` | Position of having been wronged in a relationship. | no |

The crisis-adjacent set is what `crisisHardExclusion.avoidWhenCrisisAdjacent` references in `vocabulary.json`. The other two values are still useful for normal shortlist exclusion when `crisisFlag = false` — they just don't trigger the stricter crisis-time filter on their own.

## emotionalFit (14 values)

**Reused verbatim from the device-side emotion vocabulary** in `hooks/sentiment-utils.ts`. The shortlist heuristic (task 4.4a) compares this field directly against the `emotions` array the device sent, so the vocabularies must match exactly.

`joy`, `sadness`, `anger`, `fear`, `surprise`, `disgust`, `hope`, `anxiety`, `peace`, `love`, `gratitude`, `frustration`, `excitement`, `confusion`.

If the device-side `EMOTIONS` constant changes, `emotionalFit` must be re-frozen and affected rows relabeled.

## vulnerableStatesToAvoid (9 values)

Same value set as `avoidWhen`. The schema keeps both fields because they answer slightly different questions in practice:

- `avoidWhen` — populated by the labeling LLM in pass 2 from the passage's tone and content. "If I read this passage in state X, will it likely harm me?"
- `vulnerableStatesToAvoid` — populated or amended by the human reviewer when they see a vulnerable state the LLM missed. Effectively a reviewer override channel.

Sharing the value set means both fields can be enforced against the same allowlist. Whether to collapse them in v2 is an open question — flagged for the rubric draft (task 2.4a).

## Crisis-flag hard exclusion

When the lookup request has `crisisFlag = true`, the adapter filters the LLM-visible index *before* the prompt is built. A passage is excluded if **any** of these match:

1. `tone` ∈ {`stern`, `warning`}
2. Any `themes` value ∈ {`death`, `ascetic-discipline`, `moral-rebuke`}
3. Any `avoidWhen` value ∈ {`acute-shame`, `panic`, `despair`, `self-blame`, `abuse-disclosure`, `fresh-grief`, `suicidal-ideation`}
4. `excludeOnCrisis == true`

The LLM is never told a crisis is in progress; it simply sees a smaller, safer index. If exclusion leaves fewer than three eligible passages, the adapter returns `lookup_unavailable` rather than relaxing the filter or substituting LLM-generated content (per spec scenario "Crisis-flag exclusion leaves fewer than three eligible passages").

The exact tones and themes listed above are the canonical hard-exclusion set for v1 and require human review before any release (task 4.9).

## Out of scope for this artifact

- Labeling rubric (task 2.4a — next session).
- Two-pass labeling prompts (task 2.5).
- JSON Schema document for labeled output (task 2.4b).
- Decision on whether to collapse `avoidWhen` and `vulnerableStatesToAvoid` in v2.
