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
                          label_catalog.py (task 3.1, TODO)
                          two passes: prompts/semantic-pass.md
                                      prompts/safety-tone-pass.md
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

# Inspect the derived JSON Schema (built live from vocabulary.json)
python3 validate.py --dump-schema
```

`seed_catalog.py` and `catalog.seed.json` are committed. `outputs/` holds
labeling-run intermediates and is gitignored. The labeling driver
(`label_catalog.py`) and provider/model selection are section 3 (tasks 3.1–3.7),
not yet built.

Pure stdlib; no pip install required for `seed_catalog.py` / `validate.py`.
The labeling driver will add provider SDK deps when section 3 lands.
