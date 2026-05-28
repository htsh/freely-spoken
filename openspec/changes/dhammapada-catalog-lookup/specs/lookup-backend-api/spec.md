## MODIFIED Requirements

### Requirement: Backend exposes POST /lookup

The hosted backend SHALL expose a `POST /lookup` JSON endpoint that accepts an anonymized sentiment payload and returns ranked references with canonical text for implemented variants.

#### Scenario: Valid Dhammapada request returns ranked catalog passages

- **WHEN** the device POSTs `{ appVariant: "dhammapada", anonymizedText, sentiment, emotions, confidence }` with a valid client secret header
- **THEN** the backend SHALL respond `200 OK` with JSON `{ primary, alternates: [Ref, Ref], provider, model, retryCount, fallbackUsed, crisisFlag }`
- **AND** each `Ref` SHALL contain `ref`, `text`, `translation`, and `shortReason`
- **AND** `alternates` SHALL contain exactly two `Ref` objects
- **AND** `text` SHALL come from the approved Dhammapada catalog, not from LLM output

### Requirement: Request validation rejects malformed payloads

The backend SHALL validate the request body and reject malformed input with `400 Bad Request`.

#### Scenario: Dhammapada is a known variant

- **WHEN** the device POSTs `appVariant: "dhammapada"` after the Dhammapada adapter is registered
- **THEN** the backend SHALL treat it as a known variant
- **AND** the request SHALL pass variant validation when all other required fields are valid
