# Labeling provider/model evaluation results (tasks 3.4–3.6)

**Decision:** Use `accounts/fireworks/models/deepseek-v4-pro` (Fireworks) for the
full-corpus labeling run. Recorded 2026-05-29.

This is the *offline labeling* provider/model. It is explicitly allowed to
differ from the runtime lookup provider/model (task 3.7) — the runtime selector
chain stays Gemini Flash → OpenRouter → Groq.

## Method

Ran the two-pass labeling driver (`tools/dhammapada-labeling/label_catalog.py`)
over the 26-passage eval sample (`eval_sample.json`, which covers every
crisis-hard-exclusion category) for two Fireworks models, with constrained
decoding (`response_format=json_schema`) on. Compared with
`compare_evals.py`. Runbook: `docs/idle-ashes-labeling-eval.md`.

Candidates were constrained to what is provisioned to the account
(`GET /v1/models` is account-scoped): the originally intended
`deepseek-v4-flash` and `qwen3p6-plus` are **not** available, so the round was
`deepseek-v4-pro` vs `kimi-k2p6`.

## Results (26-passage sample)

| Metric | deepseek-v4-pro | kimi-k2p6 |
|---|---|---|
| Rows labeled | 26/26 | 26/26 |
| JSON failures | 0 | 0 |
| Vocab failures | 0 | 0 |
| Avg latency | 24.45 s | 3.01 s |
| Prompt tokens | 49,970 | 31,738 |
| Completion tokens | 53,110 | 5,399 |

Format compliance is identical (constrained decoding guarantees it), so the
decision is judgment, not format. Tone exact-match between the two was only
11/26 (42%) — a stylistic split (deepseek favors descriptive tones
`aphoristic`/`contemplative`; kimi favors directive `stern`/`exhortative`),
both in-vocabulary.

## Rationale

The deciding axis was `avoidWhen` / `vulnerableStatesToAvoid` breadth on the
high-risk passages:

- **deepseek is systematically more conservative.** On dhp-307 ("evil-doers go
  to hell") it tags `despair, fresh-grief, suicidal-ideation, panic` in
  `avoidWhen`; kimi tags only `acute-shame, self-blame, abuse-disclosure`. Both
  models keep harsh tone on dhp-017/dhp-307 and `fresh-grief` on
  dhp-277/dhp-287, so the crisis hard-exclusion catches those either way; the
  gap is in the **non-crisis** shortlist, where only `avoidWhen` protects a
  sub-crisis vulnerable user. deepseek covers that margin; kimi leaves a gap.
- **Counter-consideration (documented, not disqualifying):** deepseek
  over-tags `avoidWhen` on milder verses (e.g. dhp-369 gets the full 9-state
  list). Left unchecked across 423 verses this risks over-suppression and more
  frequent `lookup_unavailable` (task 4.8). The human review gate (task 2.8)
  will **trim** over-broad `avoidWhen` on review rather than backfill missing
  ones — the safer direction to correct from for a wellbeing-adjacent v1.
- Cost/latency favor kimi ~10×, but the full corpus is <$1 either way, so cost
  is a tiebreaker only.

Chose deepseek-v4-pro: for a v1 wellbeing product, erring toward withholding is
the correct institutional bias, and over-tagging is easier and safer for human
review to correct than under-tagging is to detect.

## Tooling fixes made during the eval (carried into the committed driver)

1. **Explicit `User-Agent` header** — Fireworks fronts its API with Cloudflare,
   which 403s urllib's default `Python-urllib/x.y` signature (CF error 1010).
2. **Timeout resilience** — default per-call read timeout raised 60 s → 180 s,
   added `--timeout`, and `call_with_retry` now catches `TimeoutError`/`OSError`
   (reasoning models are slow; a single slow call no longer aborts the run).

## Next

- Task 2.6: full-corpus run with deepseek-v4-pro → `outputs/catalog.labeled.json`.
- Task 2.8: human review of high-risk labels (trim over-broad `avoidWhen`, set
  `excludeOnCrisis`, populate `reviewedBy`) before promotion to
  `server/app/lookup/dhammapada_catalog.json`.
