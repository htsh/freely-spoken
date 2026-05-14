#!/usr/bin/env bash
# Confirms the Stoic variant returns the not-implemented stub at HTTP 200.
set -euo pipefail

HOST="${HOST:-http://localhost:8080}"
SECRET="${LOOKUP_CLIENT_SECRET:-}"

curl -sS -X POST "$HOST/lookup" \
  -H 'Content-Type: application/json' \
  ${SECRET:+-H "X-Lookup-Client-Secret: $SECRET"} \
  -d '{
    "appVariant": "stoic",
    "anonymizedText": "the person is feeling anxious about a recent change",
    "sentiment": "negative",
    "emotions": ["anxiety"],
    "confidence": 60
  }' | python3 -m json.tool
