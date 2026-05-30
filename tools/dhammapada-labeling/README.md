# Dhammapada labeling tool (dev-only data prep)

Offline data-prep for the Dhammapada (Idle Ashes / `appVariant: "dhammapada"`)
catalog. Not part of the runtime server. Produces the curated catalog that the
backend adapter loads at runtime.

Key committed artifacts:

- `catalog.seed.json` — deterministic seed catalog from Project Gutenberg #2017
- `vocabulary.json` — frozen controlled vocabularies (v1.0)
- `prompts/` — the two labeling passes used for retrieval metadata
- `validate.py` — schema, vocabulary, and cross-field validation
- `labeled/` — backed-up labeled/adjudicated catalog snapshots

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
                              human review
                                        │
                                        ▼
                  server/app/lookup/dhammapada_catalog.json
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

# Provider/model evaluation over the curated 26-passage sample
export FIREWORKS_API_KEY=...        # or HF_TOKEN / GROQ_API_KEY / OPENROUTER_API_KEY / ...
python3 label_catalog.py --provider fireworks \
    --model accounts/fireworks/models/llama-v3p1-70b-instruct \
    --sample eval_sample.json --out outputs/eval.fireworks-70b.json
python3 validate.py outputs/eval.fireworks-70b.json --require-labeled --subset

# Full corpus run after a model is chosen
# --concurrency parallelizes rows (slow reasoning models otherwise take hours);
# the 429 backoff in call_with_retry handles rate limits.
python3 label_catalog.py --provider <p> --model <m> \
    --concurrency 8 --timeout 240 --out outputs/catalog.labeled.json
```

`seed_catalog.py`, `validate.py`, `label_catalog.py`, the prompts, and
`catalog.seed.json` / `eval_sample.json` are committed. `outputs/` holds
disposable labeling-run scratch and is gitignored.

`labeled/` is **committed** — it durably backs up full-corpus label runs (the
raw model output is expensive to regenerate). Files are named
`catalog.labeled.<model>.<promptVersion>.json` plus a `.report.json` sidecar.
This is a **pre-review intermediate**, NOT the runtime catalog: it has machine
labels only (`reviewedBy: null`, `excludeOnCrisis: false` on every row). It is
promoted to `server/app/lookup/dhammapada_catalog.json` only after
human review trims over-broad `avoidWhen`, sets `excludeOnCrisis`,
and populates `reviewedBy` on the high-risk rows.

**Providers:** `label_catalog.py` speaks the OpenAI-compatible
`/chat/completions` API, so one client covers Fireworks, HF router, Groq,
OpenRouter, Together, and Cerebras — pick with `--provider`, set the matching
`*_API_KEY` env var. `mock` needs no key (offline plumbing). `replicate` is a
stub: its create-prediction + poll API is not OpenAI-compatible; wire a client
only if a Replicate-hosted model wins the eval. Model IDs are **account-scoped**
on Fireworks — `GET /v1/models` lists only what's provisioned to your account,
not the full web catalog; confirm an ID is live before a run. The client sends
an explicit `User-Agent` because Fireworks fronts its API with Cloudflare, which
403s urllib's default `Python-urllib/x.y` signature (CF error 1010).

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
provider comparison.

Pure stdlib; no pip install required.
