## ADDED Requirements

### Requirement: System supports multiple lookup variants

The harness SHALL support at least two variant modes: Christian and Stoic.

#### Scenario: Variant toggle present

- **WHEN** the user loads the index page
- **THEN** the UI SHALL display a toggle to select between "Christian" and "Stoic" variants

### Requirement: Christian adapter is fully functional

The Christian variant SHALL perform real verse selection via Gemini Flash.

#### Scenario: Christian variant selected

- **WHEN** the user selects the Christian variant and runs a sample
- **THEN** the system SHALL use the Christian lookup adapter
- **AND** the adapter SHALL call Gemini Flash with a Christian-specific system prompt
- **AND** the adapter SHALL return a valid LookupResult with references

### Requirement: Stoic adapter returns a stub payload

The Stoic variant SHALL be wired end-to-end but return a clear "not yet implemented" response.

#### Scenario: Stoic variant selected

- **WHEN** the user selects the Stoic variant and runs a sample
- **THEN** the system SHALL use the Stoic lookup adapter
- **AND** the adapter SHALL return a payload indicating the variant is not yet implemented
- **AND** the result page SHALL render the stub message clearly

#### Scenario: Stoic toggle is disabled with tooltip

- **WHEN** the Stoic variant is not yet implemented
- **THEN** the Stoic toggle MAY be visually disabled
- **AND** a tooltip or label SHALL indicate "catalog not yet seeded"

### Requirement: Adding a variant requires only a new adapter

The variant system SHALL be extensible such that adding a new tradition requires only implementing a new adapter.

#### Scenario: Extending to a new variant

- **WHEN** a developer creates a new file implementing the LookupAdapter protocol
- **THEN** the system SHALL recognize the new variant without changes to routing, templates, or core pipeline code
