## ADDED Requirements

### Requirement: Backend supports dhammapada appVariant

The backend SHALL support `appVariant: "dhammapada"` after the Dhammapada catalog and adapter are implemented.

#### Scenario: Dhammapada request dispatches to Dhammapada adapter

- **WHEN** the backend receives a valid lookup request with `appVariant: "dhammapada"`
- **THEN** it SHALL dispatch the request to the registered Dhammapada adapter
- **AND** it SHALL return the same ranked-reference response shape used by implemented lookup variants

### Requirement: Device can be built as Dhammapada variant

The device app SHALL allow a build-time Dhammapada app variant without changing the privacy payload.

#### Scenario: Dhammapada build sends dhammapada variant

- **WHEN** a Dhammapada build initiates a lookup
- **THEN** the request body SHALL include `appVariant: "dhammapada"`
- **AND** the request body SHALL NOT include raw transcript, audio path, recording duration, device identifiers, account data, or persistent session identifiers

### Requirement: Device labels Dhammapada results as passages

The device results screen SHALL use Dhammapada-specific presentation copy for the Dhammapada variant.

#### Scenario: Dhammapada build renders results

- **WHEN** the device renders results for a Dhammapada build
- **THEN** UI copy SHALL refer to the primary item as a "passage" or "Dhammapada passage"
- **AND** UI copy SHALL NOT refer to the result as a Bible verse
