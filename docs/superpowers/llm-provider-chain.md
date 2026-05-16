# LLM Provider Chain — Free Tier Budget

Live document. Free-tier limits change; update this when a provider breaks or a new one is added.

## Current chain

Order is configurable via `LOOKUP_PROVIDER_ORDER` (default: `gemini,openrouter,groq,cloudflare`). The runner in `server/app/llm_runner.py` walks this list, immediately falling back on 429, retrying with jitter on 5xx/timeout.

### 1. Gemini Flash (primary)

- **Model**: `gemini-2.0-flash`
- **Auth**: `GEMINI_API_KEY` via Google AI Studio
- **Timeout**: 30s
- **Free tier**: ~1,500 requests/day, ~15 RPM
- **Caveats**: generous daily cap but low RPM; hits 429 quickly during spikes. JSON-mode (`responseMimeType: application/json`) is reliable.
- **Code**: `server/app/providers/gemini.py`

### 2. OpenRouter free

- **Model**: `openrouter/free` (rotates across free-tier models)
- **Auth**: `OPENROUTER_API_KEY`
- **Timeout**: 30s
- **Free tier**: hard to pin down — depends on which underlying model services the request. Expect ~10–30 RPM with queueing during peak hours.
- **Caveats**: latency varies wildly (10–30s queue times common). The `/free` route is a meta-model; you don’t control which backend handles it.
- **Code**: `server/app/providers/openrouter.py`

### 3. Groq

- **Model**: `llama-3.1-8b-instant`
- **Auth**: `GROQ_API_KEY`
- **Timeout**: 30s
- **Free tier**: ~20 RPM, ~3,000–5,000 requests/day (historically; check current dashboard)
- **Caveats**: extremely fast when it works, but the free tier is the most aggressively rate-limited of the three. Burns out quickly under sustained load.
- **Code**: `server/app/providers/groq.py`

### 4. Cloudflare Workers AI

- **Model**: `@cf/meta/llama-3.1-8b-instruct`
- **Auth**: `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_API_TOKEN`
- **Timeout**: 30s
- **Free tier**: ~10,000 requests/day on Workers free tier
- **Caveats**: requires Cloudflare account; Workers AI free tier generous but rate-limits per model. Good deep fallback after Groq burns out.
- **Code**: `server/app/providers/cloudflare.py`

## Candidate providers (not yet wired)

These are the next candidates to slot into `server/app/providers/` and `PROVIDERS` in `llm_runner.py`. Pattern: async `generate(system_prompt, user_prompt) -> str` plus a typed `*Error(Exception)`.

### Cloudflare Workers AI

- **Model**: `@cf/meta/llama-3.1-8b-instruct` or similar
- **Auth**: Cloudflare account ID + API token
- **Free tier**: ~10,000 requests/day on the Workers free tier
- **Pros**: high daily cap, decent RPM, fast edge inference
- **Cons**: requires Cloudflare account; model selection is limited to their catalog
- **API**: REST endpoint at `https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}`

### Cohere

- **Model**: `command-r` or `command-r-plus`
- **Auth**: `COHERE_API_KEY`
- **Free tier**: exists but rate-limited; exact numbers shift. Expect ~5 RPM, ~1,000 requests/day.
- **Pros**: solid JSON adherence
- **Cons**: lower daily cap than Gemini; not obviously better than existing options

### Mistral La Plateforme

- **Model**: `mistral-small-latest` or `open-mistral-nemo`
- **Auth**: `MISTRAL_API_KEY`
- **Free tier**: ~1 RPM, ~500 requests/day for the smallest tier
- **Pros**: good at following structured output instructions
- **Cons**: very low RPM — only useful as a deep fallback, not for spikes

### Together AI

- **Model**: `meta-llama/Llama-3.1-8B-Instruct` or similar
- **Auth**: `TOGETHER_API_KEY`
- **Free tier**: exists for some models, ~10–20 RPM
- **Pros**: fast inference, good model selection
- **Cons**: free tier is model-specific and may disappear

### Fireworks AI

- **Model**: `accounts/fireworks/models/llama-v3p1-8b-instruct`
- **Auth**: `FIREWORKS_API_KEY`
- **Free tier**: exists but limited; ~10 RPM, ~1,000 requests/day
- **Pros**: fast, good at JSON
- **Cons**: smaller free tier than Cloudflare

### DeepSeek API

- **Model**: `deepseek-chat`
- **Auth**: `DEEPSEEK_API_KEY`
- **Free tier**: exists but often congested; ~10 RPM
- **Pros**: cheap even if paid; good reasoning
- **Cons**: high latency (10–60s), free tier queue times are unpredictable. Good as a last-resort fallback only.

## Rough daily budget estimate

If all current providers are wired and operating at free-tier limits:

| Provider | Est. daily requests |
|---|---|
| Gemini Flash | 1,500 |
| OpenRouter free | 1,000–2,000 (volatile) |
| Groq | 3,000–5,000 |
| Cloudflare | 10,000 |
| **Current total** | **~15,500–18,500** |

If all candidate providers are also wired:

| Provider | Est. daily requests |
|---|---|
| Cohere | 1,000 |
| Together AI | 1,000–2,000 |
| Fireworks | 1,000 |
| Mistral | 500 |
| DeepSeek | 500–1,000 (congested) |
| **Total with candidates** | **~19,000–24,000** |

That is plenty for a soft launch with a per-device daily cap of 3 lookups. At 100 DAU = 300 requests/day. At 1,000 DAU = 3,000/day.

## How to add a new provider

1. Create `server/app/providers/<name>.py` with:
   - `NAME = "<name>"`
   - `MODEL = "<model-id>"`
   - `class <Name>Error(Exception)`
   - `async def generate(system_prompt: str, user_prompt: str) -> str`
2. Import it in `server/app/llm_runner.py` and add to `PROVIDERS` dict.
3. Add the error class to `_ERRORS` tuple in `llm_runner.py`.
4. Update `LOOKUP_PROVIDER_ORDER` (env var) to include it in the desired position.
5. Add the env var name and free-tier notes to this doc.

## Operational notes

- All providers use a 30-second `httpx` timeout. If a provider routinely queues longer than that, raise the timeout in its module or skip it.
- The runner logs `unknown_provider_in_order` if a name in `LOOKUP_PROVIDER_ORDER` is not in `PROVIDERS`. This is your signal that the env var is out of sync with code.
- `fallback_used` in the response metadata tells you which provider handled the request. Log this to see which tier is doing the heavy lifting.
- If you hit `AllProvidersFailedError`, the response propagates to the device as a lookup error. The app should show a generic retry message, not provider-specific copy.

## “Sorry, come back tomorrow”

Not yet implemented. The backend currently has no per-user or per-device quota. When the free pool is exhausted, the user sees a generic error.

Planned: add a lightweight daily quota (e.g., 3 lookups/device) gated by a hash of the `lookupClientSecret` or a rotating token. When quota is exhausted, return `{ status: "daily_limit", retryAfter: "tomorrow" }` and the app shows friendly copy.
