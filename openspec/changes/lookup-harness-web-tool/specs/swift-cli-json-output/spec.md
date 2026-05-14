## ADDED Requirements

### Requirement: CLI accepts --json flag

The sentiment-cli executable SHALL accept a `--json` command-line flag.

#### Scenario: Invoking with --json

- **WHEN** the user runs `swift run sentiment-cli --json "sample text"`
- **THEN** the program SHALL output valid JSON to stdout

### Requirement: --json output is structured sentiment data

When `--json` is passed, the CLI SHALL emit a single JSON object containing sentiment analysis fields.

#### Scenario: JSON contains required fields

- **WHEN** the CLI runs with `--json` on any input text
- **THEN** the JSON object SHALL contain the fields: `sentiment`, `emotions`, `confidence`, `anonymizedText`, `rawStrategy`, `raw`

#### Scenario: JSON is parseable

- **WHEN** the CLI runs with `--json`
- **THEN** the output SHALL be valid JSON with no surrounding prose, headers, or debug logs

### Requirement: --json does not alter existing behavior

The `--json` flag SHALL be additive. All existing CLI behavior SHALL remain unchanged when `--json` is not provided.

#### Scenario: Default output unchanged

- **WHEN** the CLI runs without `--json`
- **THEN** the output SHALL match the existing human-readable format

#### Scenario: --raw flag unchanged

- **WHEN** the CLI runs with `--raw`
- **THEN** the output SHALL match the existing `--raw` behavior regardless of `--json` presence
