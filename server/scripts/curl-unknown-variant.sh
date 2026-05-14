#!/usr/bin/env bash
# Should return 400 / unknown_variant.
set -euo pipefail

HOST="${HOST:-http://localhost:8080}"
SECRET="${LOOKUP_CLIENT_SECRET:-}"

curl -sS -X POST "$HOST/lookup" \
  -H 'Content-Type: application/json' \
  ${SECRET:+-H "X-Lookup-Client-Secret: $SECRET"} \
  -w '\nHTTP %{http_code}\n' \
  -d '{
    "appVariant": "buddhist",
    "anonymizedText": "the person is uncertain",
    "sentiment": "neutral",
    "emotions": [],
    "confidence": 50
  }'
