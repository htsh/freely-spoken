## ADDED Requirements

### Requirement: LLM selects references, never returns scripture text

The Christian adapter SHALL prompt the LLM to return Bible references only — no canonical scripture text.

#### Scenario: LLM output contains only references

- **WHEN** the Christian adapter calls the LLM
- **THEN** the LLM response SHALL be a JSON object with `primary` and `alternates`
- **AND** each item SHALL have only `ref` and `shortReason` fields
- **AND** the adapter SHALL reject any response containing extended scripture quotations in `shortReason`

### Requirement: Backend fetches canonical text from Bible API

The Christian adapter SHALL fetch canonical verse text from the configured Bible API for every reference returned by the LLM, before responding to the device.

#### Scenario: All references fetched successfully

- **WHEN** the LLM returns 1 primary + 2 alternate references
- **THEN** the adapter SHALL call the Bible API for each reference in parallel
- **AND** each `Ref` in the response SHALL include `text` (canonical verse text) and `translation` (translation name returned by the API)

#### Scenario: One reference fetch fails

- **WHEN** the Bible API call for one reference fails (network error, 4xx, 5xx, or empty body)
- **THEN** that `Ref` SHALL include `textError: <string>` instead of `text`
- **AND** the other references SHALL be returned normally with text populated
- **AND** the overall response SHALL still be `200 OK`

#### Scenario: All Bible API calls fail

- **WHEN** every reference fetch fails
- **THEN** the backend SHALL return `502` with `{ error: { code: "bible_api_down", message } }`

### Requirement: Reference format is single-verse

Each reference SHALL match the single-verse format `^[1-3]?\s?[A-Za-z]+\s\d+:\d+(-\d+)?$`.

#### Scenario: LLM returns an invalid reference

- **WHEN** the LLM response contains a `ref` that does not match the pattern
- **THEN** the adapter SHALL treat the LLM response as malformed and fall through to the next provider (or return `all_providers_failed` if exhausted)

### Requirement: shortReason is short, plain modern English

Each `shortReason` SHALL be 1-3 sentences of plain modern English.

#### Scenario: LLM returns a too-long reason

- **WHEN** an LLM response contains a `shortReason` with more than 3 sentences
- **THEN** the adapter SHALL treat the response as malformed and fall through to the next provider

### Requirement: Bible API client is config-driven

The Bible API base URL and default translation SHALL be configurable via environment variables.

#### Scenario: Operator points at a self-hosted mirror

- **WHEN** `BIBLE_API_URL` is set to a mirror URL
- **THEN** every Bible API call SHALL go to the mirror

#### Scenario: Operator changes default translation

- **WHEN** `BIBLE_TRANSLATION` is set
- **THEN** every reference SHALL be fetched in that translation
- **AND** the response `translation` field SHALL reflect the API's name for that translation

### Requirement: Canonical text fetches are cached per-process

The backend SHALL cache successful Bible API responses keyed by `(ref, translation)` for the lifetime of the process.

#### Scenario: Repeat reference within process lifetime

- **WHEN** the LLM picks a reference that has been fetched before in the same process
- **THEN** the backend SHALL serve the cached text without calling the Bible API again
