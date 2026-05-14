## ADDED Requirements

### Requirement: Backend exposes POST /lookup

The hosted backend SHALL expose a `POST /lookup` JSON endpoint that accepts an anonymized sentiment payload and returns ranked references with canonical text.

#### Scenario: Valid Christian request returns ranked references

- **WHEN** the device POSTs `{ appVariant: "christian", anonymizedText, sentiment, emotions, confidence }` with a valid client secret header
- **THEN** the backend SHALL respond `200 OK` with JSON `{ primary, alternates: [Ref, Ref], provider, model, retryCount, fallbackUsed, crisisFlag }`
- **AND** each `Ref` SHALL contain `ref`, `text`, `translation`, and `shortReason`
- **AND** `alternates` SHALL contain exactly two `Ref` objects

### Requirement: Request validation rejects malformed payloads

The backend SHALL validate the request body and reject malformed input with `400 Bad Request`.

#### Scenario: Missing required field

- **WHEN** the device POSTs a request missing `anonymizedText`, `sentiment`, `emotions`, `confidence`, or `appVariant`
- **THEN** the backend SHALL return `400` with `{ error: { code: "invalid_request", message } }`

#### Scenario: Unknown variant

- **WHEN** the device POSTs `appVariant` that is not `"christian"` or `"stoic"`
- **THEN** the backend SHALL return `400` with `{ error: { code: "unknown_variant", message } }`

### Requirement: Provider fallback chain

The backend SHALL try LLM providers in a configured order, falling back on rate-limit or transient failures.

#### Scenario: Primary returns 429, fallback succeeds

- **WHEN** the primary provider returns HTTP `429`
- **THEN** the backend SHALL immediately try the next provider in the configured order
- **AND** the final response SHALL set `fallbackUsed: true` and `provider` to the provider that succeeded

#### Scenario: Transient failure triggers bounded retry with jitter

- **WHEN** a provider returns `500`, `502`, `503`, `504`, or a network timeout
- **THEN** the backend SHALL retry up to the configured retry cap with jittered backoff
- **AND** `retryCount` SHALL reflect the number of retries performed before success

#### Scenario: All providers exhausted

- **WHEN** every provider in the chain has been tried and all failed
- **THEN** the backend SHALL return `502` with `{ error: { code: "all_providers_failed", message } }`

### Requirement: Crisis flag is computed and returned

The backend SHALL scan the anonymized text for crisis keywords and return a `crisisFlag` boolean alongside the lookup result.

#### Scenario: Anonymized text contains a crisis keyword

- **WHEN** the anonymized text contains any keyword in the crisis list (e.g. "suicide", "self-harm", "kill myself")
- **THEN** the response SHALL include `crisisFlag: true`
- **AND** the lookup SHALL still proceed and return references normally

#### Scenario: Anonymized text does not contain crisis keywords

- **WHEN** the anonymized text contains no crisis keywords
- **THEN** the response SHALL include `crisisFlag: false`

### Requirement: Backend does not log anonymized text body

The backend SHALL log request metadata to stdout but SHALL NOT log the `anonymizedText` field.

#### Scenario: Successful request log line

- **WHEN** a request completes
- **THEN** the log entry SHALL include request id, `appVariant`, `sentiment`, emotion list, confidence, provider, retry count, fallback flag, and latency
- **AND** the log entry SHALL NOT contain the `anonymizedText` body

### Requirement: Backend requires client secret header

The backend SHALL require a configured client secret header on every request when `LOOKUP_CLIENT_SECRET` is set.

#### Scenario: Missing or wrong client secret

- **WHEN** the `LOOKUP_CLIENT_SECRET` env var is set on the backend and the request header is missing or does not match
- **THEN** the backend SHALL return `401 Unauthorized` with `{ error: { code: "unauthorized", message } }`

### Requirement: Configurable provider order and retry policy

The backend SHALL read provider order and retry policy from environment variables.

#### Scenario: Operator overrides provider order

- **WHEN** the env var `LOOKUP_PROVIDER_ORDER` is set (e.g. `"groq,gemini,openrouter"`)
- **THEN** the backend SHALL try providers in that order on the next request

#### Scenario: Operator overrides retry cap

- **WHEN** the env var `LOOKUP_MAX_RETRIES` is set
- **THEN** the backend SHALL not retry any single provider more than that many times before falling through to the next provider
