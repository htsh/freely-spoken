## ADDED Requirements

### Requirement: Pipeline includes a responseLookup state

The device app state machine SHALL include a `responseLookup` state inserted between `processing` and `results`.

#### Scenario: Sentiment completes, lookup begins

- **WHEN** on-device sentiment analysis completes successfully
- **THEN** the state machine SHALL advance from `processing` to `responseLookup`
- **AND** the lookup hook SHALL be invoked with the anonymized text and sentiment metadata

#### Scenario: Lookup completes, results render

- **WHEN** the lookup hook returns a successful result
- **THEN** the state machine SHALL advance from `responseLookup` to `results`
- **AND** the results screen SHALL render

#### Scenario: Lookup fails

- **WHEN** the lookup hook returns an error
- **THEN** the state machine SHALL advance to `results` with the error rendered
- **AND** the results screen SHALL offer a manual retry that re-invokes the lookup hook with the same input

### Requirement: useSpiritualResponseLookup hook shape

The new hook `hooks/use-spiritual-response-lookup.ts` SHALL expose `{ result, isLoading, error, lookup, reset }`.

#### Scenario: lookup() triggers the network call

- **WHEN** the consumer calls `lookup({ anonymizedText, sentiment, emotions, confidence, appVariant })`
- **THEN** the hook SHALL set `isLoading: true`, clear `error` and `result`, and make a single `POST /lookup` to `LOOKUP_API_URL`
- **AND** on success the hook SHALL set `result` and clear `isLoading`
- **AND** on error the hook SHALL set `error` to the backend error message (or a network error message) and clear `isLoading`

#### Scenario: reset() returns the hook to initial state

- **WHEN** the consumer calls `reset()`
- **THEN** `result`, `error`, and `isLoading` SHALL all return to their initial values

### Requirement: No on-device retries

The device hook SHALL make exactly one HTTP request per `lookup()` call.

#### Scenario: Backend returns 5xx

- **WHEN** the backend returns any non-2xx response
- **THEN** the hook SHALL surface the error and SHALL NOT retry automatically

### Requirement: Lookup client is typed and centralized

A single module `services/lookup-client.ts` SHALL own the HTTP call, request/response types, and `LOOKUP_API_URL` resolution.

#### Scenario: API URL resolution

- **WHEN** the lookup client is invoked
- **THEN** it SHALL read `LOOKUP_API_URL` from `expo-constants` `extra`
- **AND** if the value is unset, it SHALL throw a clearly named error before making any network call

#### Scenario: Client secret header attached

- **WHEN** a `LOOKUP_CLIENT_SECRET` is present in `expo-constants` `extra`
- **THEN** the lookup client SHALL attach it as a request header

### Requirement: Results screen renders the verse, alternates, and crisis banner

The results screen SHALL display the canonical verse content returned by the backend.

#### Scenario: Successful Christian result renders

- **WHEN** the lookup result is a Christian success payload
- **THEN** the screen SHALL display the primary `ref`, `text`, `translation`, and `shortReason`
- **AND** the screen SHALL display the two alternates as a collapsible section showing `ref`, `text`, `translation`, and `shortReason`
- **AND** the screen SHALL continue to display the existing sentiment / emotions / confidence section

#### Scenario: Crisis flag shows a non-blocking banner

- **WHEN** the lookup result includes `crisisFlag: true`
- **THEN** the screen SHALL render a non-blocking banner above the verse content
- **AND** the verse content SHALL still render normally

#### Scenario: Reference text failed to fetch

- **WHEN** a `Ref` in the result has `textError` instead of `text`
- **THEN** the screen SHALL display the `ref` and `shortReason` and an inline indicator that the canonical text could not be fetched
- **AND** the screen SHALL NOT display LLM-generated scripture text in place of the missing fetch

### Requirement: No retries or audio/transcript on the wire

The device SHALL never send the raw audio file, the unredacted transcript, or any other PII over the network.

#### Scenario: Request body contents

- **WHEN** the device sends a lookup request
- **THEN** the request body SHALL contain only `appVariant`, `anonymizedText`, `sentiment`, `emotions`, and `confidence`
- **AND** the request body SHALL NOT contain the raw transcript, audio file bytes, audio file path, recording duration, or device identifiers
