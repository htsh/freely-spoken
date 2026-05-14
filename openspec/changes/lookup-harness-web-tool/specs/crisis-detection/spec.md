## ADDED Requirements

### Requirement: Crisis keywords are detected in anonymized text

The system SHALL scan anonymized text for a configurable list of crisis-related keywords.

#### Scenario: Crisis language detected

- **WHEN** the anonymized text contains keywords such as "suicide", "self-harm", "hurt myself", "kill myself", or "end it all"
- **THEN** the system SHALL set `crisisFlag` to `true`

#### Scenario: No crisis language

- **WHEN** the anonymized text contains none of the crisis keywords
- **THEN** the system SHALL set `crisisFlag` to `false`

### Requirement: Crisis flag does not block pipeline execution

A positive crisis flag SHALL not prevent the run from completing the full pipeline.

#### Scenario: Flagged run proceeds normally

- **WHEN** a run is flagged with crisis language
- **THEN** the Swift CLI subprocess SHALL still execute
- **AND** the LLM verse lookup SHALL still execute
- **AND** the result page SHALL still render with all fields

### Requirement: Crisis flag is UI-visible only

The crisis flag SHALL affect only the user interface, not the LLM prompt or backend behavior.

#### Scenario: Crisis banner displayed

- **WHEN** a run completes with `crisisFlag: true`
- **THEN** the result page SHALL display a visible crisis banner
- **AND** the crisis flag SHALL not be included in the LLM prompt

### Requirement: Crisis keywords are configurable

The list of crisis keywords SHALL be defined in a single location for easy modification.

#### Scenario: Adding a new crisis keyword

- **WHEN** a developer adds a keyword to the crisis keyword list
- **THEN** subsequent runs SHALL detect the new keyword without code changes elsewhere
