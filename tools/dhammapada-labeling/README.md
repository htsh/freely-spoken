# Dhammapada labeling tool (dev-only data prep)

Offline data-prep for the Dhammapada (Idle Ashes / `appVariant: "dhammapada"`)
catalog. Not part of the runtime server. Produces the curated catalog that the
backend adapter loads at runtime (task 5.2).

Governing artifacts live with the OpenSpec change
(`openspec/changes/dhammapada-catalog-lookup/`):

- `rights-review.md` — source/license (F. Max Müller, PG #2017, public domain)
- `catalog-schema.md` — catalog row schema + validation invariants
- `vocabulary.json` / `vocabulary.md` — frozen controlled vocabularies (v1.0)
- `labeling-rubric.md` — what each label means + good/bad examples
- `labeled-output-schema.md` — the per-pass JSON contract the model returns

## Pipeline

```
PG #2017 HTML ──seed_catalog.py──► catalog.seed.json   (canonical text, 414 rows)
                                        │
                          label_catalog.py (two passes:
                            prompts/semantic-pass.md
                            prompts/safety-tone-pass.md)
                                        │
                                        ▼
                              outputs/catalog.labeled.json  (gitignored)
                                        │
                                  validate.py
                                        │
                              human review (task 2.8)
                                        │
                                        ▼
                  server/app/lookup/dhammapada_catalog.json  (task 5.2)
```

## Commands

```bash
# Re-seed canonical text from Project Gutenberg (deterministic; commit result)
python3 seed_catalog.py --grouping passage --out catalog.seed.json

# Validate a seed or labeled catalog against the frozen schema + vocabulary
python3 validate.py catalog.seed.json
python3 validate.py outputs/catalog.labeled.json --require-labeled
python3 validate.py outputs/eval.fireworks.json --require-labeled --subset  # eval subset

# Inspect the derived JSON Schema (built live from vocabulary.json)
python3 validate.py --dump-schema

# Offline plumbing test — no API key (deterministic mock provider)
python3 label_catalog.py --provider mock --sample eval_sample.json --out outputs/mock.json

# Provider/model evaluation over the curated 26-passage sample (task 3.4)
export FIREWORKS_API_KEY=...        # or HF_TOKEN / GROQ_API_KEY / OPENROUTER_API_KEY / ...
python3 label_catalog.py --provider fireworks \
    --model accounts/fireworks/models/llama-v3p1-70b-instruct \
    --sample eval_sample.json --out outputs/eval.fireworks-70b.json
python3 validate.py outputs/eval.fireworks-70b.json --require-labeled --subset

# Full corpus run (after a model is chosen, task 2.6)
python3 label_catalog.py --provider <p> --model <m> --out outputs/catalog.labeled.json
```

`seed_catalog.py`, `validate.py`, `label_catalog.py`, the prompts, and
`catalog.seed.json` / `eval_sample.json` are committed. `outputs/` holds
labeling-run intermediates and is gitignored.

**Providers:** `label_catalog.py` speaks the OpenAI-compatible
`/chat/completions` API, so one client covers Fireworks, HF router, Groq,
OpenRouter, Together, and Cerebras — pick with `--provider`, set the matching
`*_API_KEY` env var. `mock` needs no key (offline plumbing). `replicate` is a
stub: its create-prediction + poll API is not OpenAI-compatible; wire a client
only if a Replicate-hosted model wins the eval.

**Structured output (on by default):** the driver sends
`response_format={"type":"json_schema",...}` with the per-pass schema built
live from `vocabulary.json` (enums + cardinality). On providers that support
constrained decoding (Fireworks does), this makes JSON validity and
in-vocabulary labels a platform guarantee, so model choice comes down to
judgment quality (tone/safety), not JSON reliability. The subset rule
(`vulnerableStatesToAvoid ⊆ avoidWhen`) isn't expressible in JSON Schema and
stays a `validate.py` check. Pass `--no-structured` for providers/models that
reject `response_format`.

Each labeling run writes `<out>` plus `<out>.report.json` (counts, JSON-valid
rate, vocab-failure rate, latency, token totals, structured flag) for the
provider comparison in task 3.5.

Pure stdlib; no pip install required.
