# Dhammapada adapter plan (Section 4)

Implementation-ready spec for `server/app/lookup/dhammapada.py` (Section 5).
`design.md` holds the architecture and rationale; this file pins the concrete
contracts Section 5 codes against. Every value here is grounded in the frozen
`vocabulary.json`, the adjudicated catalog
(`tools/dhammapada-labeling/labeled/catalog.labeled.v1.1.adjudicated.json`, promoted
to `server/app/lookup/dhammapada_catalog.json` in task 5.2), and the existing
`christian.py` / `base.py` / `main.py` contracts.

Status: planning only. No runtime code lands in this change.

---

## 4.0 Request contract change (prerequisite for 4.6/4.7)

The base `LookupRequest` (base.py) carries `anonymized_text, sentiment, emotions,
confidence` — **no `crisisFlag`**. `crisis_flag` is computed in `main.py:122`
(`check_crisis`) *after* the adapter is selected and is currently only attached to
the response, never passed into `adapter.select()`. The Dhammapada adapter needs it
*before* building the index (4.7).

Decision: thread `crisis_flag` into the adapter. Two acceptable shapes; Section 5
picks one:

- **(preferred) Add `crisis_flag: bool = False` to `LookupRequest`.** `main.py`
  computes `crisis_flag` (it already does) and sets it on the `LookupRequest` it
  constructs. Christian/Stoic ignore the field — zero behavior change for them.
  Keeps the `LookupAdapter` Protocol (`select(req) -> LookupResult`) intact.
- (alt) Add `crisis_flag` as a second `select()` argument. Rejected: changes the
  Protocol signature and every adapter's method, for one variant's need.

Also: `LookupRequestBody.appVariant` (schemas.py:7) and `LookupRequest` are
`Literal["christian", "stoic"]` today — task 5.5 widens both to include
`"dhammapada"`. Out of scope for this planning doc beyond noting the dependency.

---

## 4.1 Selector system prompt

ID-only selection from the *provided* (already shortlisted + crisis-filtered)
index. The prompt never mentions crisis state (4.7). Mirrors the Christian prompt's
structure so the JSON extractor and validation reuse the same shape.

```
You are a Dhammapada passage selector. You are given a person's anonymized
emotional situation and a numbered catalog of candidate Dhammapada passages, each
with an id and short retrieval metadata (themes, when-useful, tone, summary). Pick
the single passage that best fits their situation, plus two strong alternates.

Return a JSON object with exactly this structure:
{
  "primary": {"id": "dhp-XXX", "shortReason": "1-3 sentences"},
  "alternates": [
    {"id": "dhp-XXX", "shortReason": "1-3 sentences"},
    {"id": "dhp-XXX", "shortReason": "1-3 sentences"}
  ]
}

Rules:
- Choose ids ONLY from the provided catalog below. Do not invent ids or use
  Dhammapada knowledge outside this list.
- Exactly one primary and exactly two alternates. All three ids must be different.
- shortReason: 1-3 sentences, plain modern English, warm but not preachy.
- Do NOT quote, paraphrase, or reproduce the passage text in shortReason. Speak
  only about why it fits the person's situation.
- Match the passage tone to the person's state. Prefer concrete, compassionate
  passages. Avoid passages that would sound blaming or harsh for someone who is
  ashamed, grieving, panicked, despairing, or blaming themselves.
- If several passages fit, prefer the more concrete and gentle one.
```

The user prompt appends the situation and the numbered candidate index (4.2):

```
Anonymized situation: {anonymized_text}
Sentiment: {sentiment}
Emotions: {comma-joined emotions}

Candidate passages:
{index_block}
```

Constrained decoding: the offline labeling driver proved `response_format`
json_schema works on the providers; runtime selection SHOULD request the same
JSON-object schema where the provider supports it, falling back to the brace-matched
`_extract_json` path (ported from christian.py) otherwise.

---

## 4.2 Compact catalog index shape (passed to the LLM)

Per-row, **canonical `text` is excluded** (privacy/anti-quotation + token budget).
Fields chosen so the LLM can match on meaning and tone without the verse:

| field      | source         | why included |
|------------|----------------|--------------|
| `id`       | catalog `id`   | the only thing the LLM may return |
| `themes`   | catalog        | topical match |
| `useWhen`  | catalog        | the primary matching signal (emotional use-case) |
| `tone`     | catalog        | lets the LLM honor the tone rule (second line of defense) |
| `summary`  | catalog        | one-line gist so it can match without the text |

`avoidWhen`, `emotionalFit`, `vulnerableStatesToAvoid`, `riskNotes`,
`excludeOnCrisis`, and all provenance/source fields are **not** sent — they drive
the deterministic shortlist + crisis filter (adapter-side), not LLM reasoning.
Sending `avoidWhen` would invite the LLM to reason about crisis state, which 4.7
forbids.

Rendered as a compact numbered block (one passage per line keeps tokens down):

```
dhp-005 | themes: anger, non-hatred, reconciliation | useWhen: resentment, conflict, reactivity | tone: gentle | For hatred does not cease by hatred at any time: hatred ceases by love.
dhp-223 | themes: anger, non-hatred, virtue | useWhen: anger, conflict, patience-needed | tone: direct | Meet anger with calm, evil with good, greed with generosity, lies with truth.
...
```

At the shortlist size (30-60 rows, 4.4) this is ~2-4K tokens — well within Gemini
Flash and cheap per call, the explicit reason design.md gives for shortlisting over
the full ~40K-token index.

---

## 4.3 Malformed-output handling

A `DhammapadaAdapterError` (mirrors `ChristianAdapterError`) is raised for any
unusable output; `main.py` maps it to the existing `502 all_providers_failed` path
(same as the Christian malformed branch). Cases and handling:

| case | detection | handling |
|------|-----------|----------|
| empty / unparseable | `_extract_json` returns empty or `json.loads` fails | raise `DhammapadaAdapterError` |
| missing `primary`/`alternates` | key check | raise |
| alternates not a list of exactly 2 | type/len check | raise |
| missing `id`/`shortReason` in any entry | key check | raise |
| id not in catalog | `id not in catalog_by_id` | raise (never fabricate text) |
| id was crisis-excluded | `id not in eligible_ids` (the filtered set) | raise — same path as nonexistent id (design.md: "if the LLM returns an excluded id, the adapter rejects the response as malformed") |
| duplicate id across primary/alternates | set-size check on the 3 ids | raise |
| shortReason not 1-3 sentences | sentence count (reuse christian.py split-on-`.`) | raise |
| shortReason contains passage text | quotation heuristic (below) | raise |

**Quotation heuristic for shortReason.** Christian uses a scripture-phrase regex;
Dhammapada has no fixed liturgical phrasing, so detect quotation structurally:
reject if shortReason contains a quoted span of ≥60 chars (`"[^"]{60,}"`), OR if a
normalized ≥8-word shingle of shortReason appears in the chosen passage's canonical
`text` (the adapter *has* the text post-validation; compare lowercased,
punctuation-stripped). This catches "the model paraphrased the verse into the
reason" without a tradition-specific phrase list.

Note: there is no provider-retry inside the adapter (matches Christian — one shot;
`run_llm` owns provider fallback). A malformed response is terminal for the request.

---

## 4.4 Default selection path: deterministic shortlist + LLM rerank

Order of operations inside `select()`:

1. Load full catalog (cached at import / module load — 414 rows, task 5.2).
2. If `crisis_flag`: compute `eligible = [r for r in catalog if not excluded(r)]`
   (4.6). Else `eligible = catalog`.
3. If `crisis_flag` and `len(eligible) < 3`: return `lookup_unavailable` (4.8) —
   checked *before* shortlisting, so a thin eligible set never silently degrades.
4. `shortlist = top N (30-60) of eligible by score` (4.4a).
5. Build index block from `shortlist` (4.2), call `run_llm` with 4.1 prompt.
6. Validate output against `{r.id for r in shortlist}` (4.3) — the LLM may only
   pick from what it was shown, so an excluded id is automatically rejected.
7. Enrich the 3 chosen ids with canonical `text` + `translation` from the catalog
   (4.5). No network fetch — text is local, unlike the Bible API.

Full-compact-index selection (design.md "Fallback") is **not built in this change**;
it is gated on 4.4b measurements. Task 8.1 re-evaluates.

## 4.4a Shortlist heuristic

Deterministic, no LLM, no embeddings. Produce the top 30-60 eligible candidates by
an additive score, then truncate. Inputs derived from the request:

- `emotions` (device EMOTIONS enum) — **same vocabulary as catalog `emotionalFit`**
  (both are the 14-value `emotionalFit` list in vocabulary.json). Direct set
  membership, the strongest clean signal.
- `useWhen_hits`: map `sentiment` + `emotions` + keyword-scanned `anonymized_text`
  onto the 22-value `useWhen` vocabulary via a checked-in lexicon
  (`USEWHEN_LEXICON`, below). This is the primary matching axis design.md calls out.
- `user_vulnerable`: states inferred from sentiment/emotions/keywords that should
  *penalize* rows whose `avoidWhen` names them (the soft, always-on version of the
  crisis filter).

Score per eligible row `r`:

```
score(r) =
    3 * |emotions ∩ r.emotionalFit|          # direct enum overlap
  + 2 * |useWhen_hits ∩ r.useWhen|           # mapped use-case overlap
  + 1 * |theme_hits ∩ r.themes|              # keyword→theme overlap
  - 4 * |user_vulnerable ∩ r.avoidWhen|      # soft avoid (non-crisis safety)
  - 1 if r.tone in {stern, warning} else 0   # mild deprioritize harsh tones always
```

Ties broken by ascending `id` (stable, deterministic). Take top `SHORTLIST_SIZE`
(default 45; tune via 4.4b). If fewer than 3 eligible rows score > 0 (sparse match),
fall back to filling the shortlist with the lowest-`id` eligible rows so the LLM
always has ≥ enough to return 1 primary + 2 alternates (the `< 3` *eligible* case is
already handled at step 3; this is the "matched poorly but eligible" case).

`USEWHEN_LEXICON` / `THEME_LEXICON` are checked-in `dict[str, list[str]]` mapping
lowercase keyword stems → vocabulary labels. Starter seed (Section 5 extends + the
fixtures in 7.1 validate):

```
"angry|anger|furious|rage|irritat"        -> useWhen: anger, reactivity ; theme: anger
"resent|grudge|bitter"                     -> useWhen: resentment       ; theme: ill-will
"said|regret saying|shouldn't have said"   -> useWhen: speech-regret    ; theme: speech
"crav|want|desire|can't stop wanting"      -> useWhen: craving          ; theme: craving
"worry|worried|anxious|anxiety|nervous"    -> useWhen: worry, restlessness
"overthink|rumin|can't stop thinking|loop" -> useWhen: rumination       ; theme: mind
"argument|fight|conflict|clash"            -> useWhen: conflict
"hurt by|betrayed|let down by"             -> useWhen: relational-hurt
"hopeless|discourag|giving up|pointless"   -> useWhen: discouragement
"proud|better than|superior"               -> useWhen: pride            ; theme: pride
"confused|lost|don't know"                 -> useWhen: confusion, doubt
"grateful|thankful|blessed"                -> useWhen: gratitude
"restless|can't sit still|agitated"        -> useWhen: restlessness
```

`user_vulnerable` lexicon (feeds the score penalty; distinct from crisis hard-exclude
which is keyword-scan-driven in `check_crisis`):

```
"ashamed|embarrass|humiliat"   -> acute-shame
"my fault|blame myself|i ruined"-> self-blame
"panic|can't breathe|terrified" -> panic
"hopeless|no point|despair"     -> despair
"grief|grieving|just lost|died" -> fresh-grief
"abused|he hit|she hit|assault" -> abuse-disclosure
```

These lexicons are **product-tuning data, human-owned**, like the labels — they get
the same fixture coverage (7.1) and are easy to review in a PR.

## 4.4b Shortlist-miss instrumentation

To justify (or never build) the full-index fallback, measure whether the shortlist
ever drops a passage the LLM would have ranked first. Cheap fixture-based check, no
prod telemetry:

- For each fixture (7.1), run selection two ways: (a) normal shortlist, (b) full
  eligible index. Record whether (a)'s primary == (b)'s primary, and whether (b)'s
  primary was present in (a)'s shortlist at all.
- A "miss" = (b) picked a passage that (a)'s shortlist never contained. Log
  miss-rate across fixtures.
- Gate: build the full-index fallback (task 8.1) only if miss-rate exceeds a
  human-set threshold (suggest ≥10% of fixtures). Until then, shortlist-only.

This lives in the test/fixture harness (Section 7), not the runtime adapter.

---

## 4.5 Mapping Dhammapada onto the `Reference` response fields

The `Reference` dataclass (`ref, shortReason, text, translation, textError`) is
reused unchanged — the device already renders it generically. Mapping:

| Reference field | Dhammapada source |
|-----------------|-------------------|
| `ref`           | catalog `displayLabel` (e.g. `"Dhammapada 1"`) — *not* the internal `id`. The `id` is an implementation detail; `ref` is user-facing. |
| `shortReason`   | LLM `shortReason` (validated) |
| `text`          | catalog `text` (canonical, local lookup by id) |
| `translation`   | `"F. Max Müller translation (public domain)"` — constant for the whole corpus (open question resolved: richer label, not bare translator name) |
| `textError`     | always `None` for Dhammapada. Text is local; there is no per-ref fetch that can fail, so the `main.py` "all textError" → `bible_api_down` branch never fires for this variant. |

Internal id↔displayLabel: the adapter keeps `catalog_by_id` for validation/enrich,
and emits `displayLabel` into `ref`. Grouped couplets (e.g. dhp covering verses
58-59) already carry a `displayLabel` like `"Dhammapada 58-59"` from the seed step,
so the response reads naturally.

---

## 4.6 Crisis-flag hard-exclusion predicate (frozen)

Fully specified by `vocabulary.json → crisisHardExclusion`. The adapter excludes a
row `r` when `crisis_flag` is true and **any** of:

```python
def excluded(r) -> bool:
    return (
        r["tone"] in {"stern", "warning"}
        or any(t in {"death", "ascetic-discipline", "moral-rebuke"} for t in r["themes"])
        or any(a in {"acute-shame", "panic", "despair", "self-blame",
                     "abuse-disclosure", "fresh-grief", "suicidal-ideation"}
               for a in r["avoidWhen"])
        or r["excludeOnCrisis"] is True
    )
```

The four sets are read **from the loaded `vocabulary.json` / catalog provenance**,
not hardcoded in the adapter, so a vocabulary version bump can't silently desync the
filter from the labels. (Section 5 may inline a copy with a test asserting it equals
`vocabulary.json`'s `crisisHardExclusion`.)

Against the current adjudicated catalog this leaves **260 of 414 rows eligible**
under crisis (verified during task 2.8). `excludeOnCrisis` is `False` for every row
today — it is the lever the recommended human confirmation pass uses to remove any
crisis-eligible passage that still reads wrong, without touching the categorical
filters.

## 4.7 Exclusion happens before the index — the LLM is never told

Step 2 of the 4.4 flow runs the 4.6 filter **before** the shortlist and prompt are
built. The selector prompt (4.1) contains no crisis language, no "the user is in
distress," no conditional. The only observable effect of `crisis_flag` is a smaller
candidate list. The LLM cannot override the filter because excluded ids are never in
the index it sees; if it somehow returns one anyway (hallucinated id), 4.3 rejects it
as malformed.

## 4.8 Too few eligible passages → `lookup_unavailable`

When `crisis_flag` and `len(eligible) < 3` (checked at step 3, before shortlisting):
the adapter returns a `lookup_unavailable` outcome rather than relax the filter, fall
to the full index, or let the LLM generate content.

Wiring: add a `LookupUnavailableError` (or a sentinel result) the adapter raises;
`main.py` maps it to a new `200`-or-`503` structured response
`{ "status": "lookup_unavailable", "appVariant": "dhammapada", "crisisFlag": true }`
— shape mirrors `StoicStubResult` (a non-`LookupResult` payload the router special-
cases). Section 5 picks status code; **device copy** (task 6.2) must render this as a
gentle "we can't offer a passage right now" state, never an error stack. With 260
eligible rows this path is effectively unreachable for any real request, but it is a
required safety floor and gets a test (7.8) that forces it with a stubbed catalog.

## 4.9 Human review of the hard-exclusion list — **OPEN, human gate**

The hard-exclusion tones/themes/avoidWhen are frozen in `vocabulary.json` (v1.0,
`frozenAt 2026-05-28`) and were reviewed at freeze, but task 4.9 requires an explicit
human sign-off on the *exclusion list as the release safety contract* before ship.
Left unchecked deliberately — same gate as the recommended human confirmation pass
over the 260 crisis-eligible rows (task 2.8). These two human reviews should happen
together: confirm the categorical list here, and spot-set `excludeOnCrisis` there.

---

## Summary of Section 5 work this unblocks

- `LookupRequest.crisis_flag` field + `main.py` sets it (4.0).
- `dhammapada.py`: catalog load/cache, `excluded()` filter, shortlist scorer +
  lexicons, prompt build, `run_llm` call, JSON validate (`DhammapadaAdapterError`),
  local text enrich, `displayLabel`→`ref` mapping, `LookupUnavailableError`.
- `schemas.py` + `base.py`: widen `appVariant` literal to include `dhammapada`.
- `main.py`: register adapter, route `lookup_unavailable` payload.
- Promote adjudicated catalog → `server/app/lookup/dhammapada_catalog.json` (5.2).
```
