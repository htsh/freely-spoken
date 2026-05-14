#!/usr/bin/env bash
# Smoke-test the Christian path. Requires server running on $HOST and a real
# GEMINI_API_KEY (or fallback provider) configured server-side.
set -euo pipefail

HOST="${HOST:-http://localhost:8080}"
SECRET="${LOOKUP_CLIENT_SECRET:-}"

curl -sS -X POST "$HOST/lookup" \
  -H 'Content-Type: application/json' \
  ${SECRET:+-H "X-Lookup-Client-Secret: $SECRET"} \
  -d '{
    "appVariant": "christian",
    "anonymizedText": "the person feels overwhelmed by a difficult situation at work",
    "sentiment": "negative",
    "emotions": ["anxiety", "frustration"],
    "confidence": 65
  }' | python3 -m json.tool
