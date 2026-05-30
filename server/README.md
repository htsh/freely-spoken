# mic-check lookup backend

Hosted FastAPI service for the iOS app's response-lookup step. The device runs sentiment + anonymization locally; this service takes the anonymized text + sentiment metadata, asks an LLM to pick a canonical reference (a Bible verse for the Christian variant), fetches the canonical text from a trusted source, and returns the result.

The Mac-local prototype lives at `tools/lookup-harness/`. That tool is for iterating prompts and provider behavior; this service is the production code path. **When changing prompts or adapters, port the same change to both** (harness for iteration, this service for the device).

## Run locally

```bash
cp .env.example .env
# fill in GEMINI_API_KEY, OPENROUTER_API_KEY, GROQ_API_KEY, LOOKUP_CLIENT_SECRET
pip install -e .
uvicorn app.main:app --reload --port 8080
```

Smoke test:

```bash
curl -X POST http://localhost:8080/lookup \
  -H 'Content-Type: application/json' \
  -H "X-Lookup-Client-Secret: $LOOKUP_CLIENT_SECRET" \
  -d '{
    "appVariant": "christian",
    "anonymizedText": "the person feels overwhelmed by a difficult situation",
    "sentiment": "negative",
    "emotions": ["anxiety", "frustration"],
    "confidence": 65
  }'
```

## Endpoints

- `POST /lookup` — main contract. Request/response shapes in `app/schemas.py`.
- `GET /healthz` — liveness probe; returns `{ "ok": true }`.

## Environment variables

| Variable                  | Purpose                                                                                              |
| ------------------------- | ---------------------------------------------------------------------------------------------------- |
| `GEMINI_API_KEY`          | Google Generative Language API key for Gemini Flash.                                                 |
| `OPENROUTER_API_KEY`      | OpenRouter API key for the free-tier fallback.                                                       |
| `GROQ_API_KEY`            | Groq Cloud API key for the second fallback.                                                          |
| `LOOKUP_CLIENT_SECRET`    | Shared secret the device sends in `X-Lookup-Client-Secret`. Unset means no auth (local dev only).    |
| `BIBLE_API_URL`           | Base URL for the Bible API. Defaults to `https://bible-api.com`. Point at a self-hosted mirror later.|
| `BIBLE_TRANSLATION`       | Translation id. Defaults to `web` (World English Bible, public domain).                              |
| `LOOKUP_PROVIDER_ORDER`   | Comma-separated provider order. Defaults to `gemini,openrouter,groq`.                                |
| `LOOKUP_MAX_RETRIES`      | Per-provider retry cap for transient (non-429) errors. Defaults to `3`.                              |
| `LOOKUP_MAX_CONCURRENCY`  | Global in-flight lookup cap. Defaults to `8`.                                                        |

## Deploy (Fly.io)

```bash
fly launch --no-deploy             # one-time; uses Dockerfile + fly.toml
fly secrets set \
  GEMINI_API_KEY=… \
  OPENROUTER_API_KEY=… \
  GROQ_API_KEY=… \
  LOOKUP_CLIENT_SECRET=…
fly deploy
fly status
curl https://<app>.fly.dev/healthz
```

### Rollback

```bash
fly releases                       # find the previous good release id
fly deploy --image registry.fly.io/<app>:deployment-<id>
```

The device falls back to the previous flow when `LOOKUP_API_URL` is unset in the build's `app.json` `extra`. A device emergency rollback is a build without that var set, no server changes required.
