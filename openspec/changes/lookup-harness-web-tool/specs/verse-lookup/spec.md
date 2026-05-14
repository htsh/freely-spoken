## ADDED Requirements

### Requirement: LLM receives structured sentiment metadata

The verse lookup adapter SHALL send a prompt to the LLM containing anonymized text, sentiment, emotions, and confidence.

#### Scenario: Constructing the LLM prompt

- **WHEN** the sentiment pipeline produces a result
- **THEN** the lookup adapter SHALL construct a prompt with fields: `Anonymized text`, `Sentiment`, `Emotions`, `Confidence`

### Requirement: LLM returns ranked verse references

The LLM SHALL return exactly one primary reference and two alternate references.

#### Scenario: Successful verse selection

- **WHEN** the lookup adapter calls the LLM with valid sentiment metadata
- **THEN** the response SHALL contain a JSON object with `primary` and `alternates` fields
- **AND** `primary` SHALL be a single Reference object
- **AND** `alternates` SHALL be an array of exactly two Reference objects

### Requirement: Reference format is valid

Each reference string SHALL match the expected Bible verse format.

#### Scenario: Valid reference format

- **WHEN** the LLM returns a reference
- **THEN** the `ref` field SHALL match the pattern `^[1-3]?\s?[A-Za-z]+\s\d+:\d+(-\d+)?$`

#### Scenario: Short reason length

- **WHEN** the LLM returns a reference
- **THEN** the `shortReason` field SHALL be between 1 and 3 sentences
- **AND** the tone SHALL be plain modern English without preaching

### Requirement: No verse text in LLM output

The LLM output SHALL contain only references and reasons, not canonical verse text.

#### Scenario: Output contains no scripture text

- **WHEN** the lookup adapter receives LLM output
- **THEN** the output SHALL not contain full Bible verses or extended scripture quotations

### Requirement: Malformed LLM output is handled gracefully

If the LLM returns malformed JSON or deviates from the schema, the harness SHALL surface the failure clearly.

#### Scenario: Invalid JSON from LLM

- **WHEN** the LLM returns unparseable or malformed JSON
- **THEN** the harness SHALL display the raw LLM output verbatim
- **AND** the run SHALL be marked as failed
- **AND** no retry SHALL be attempted automatically
