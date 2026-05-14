## ADDED Requirements

### Requirement: Device sends appVariant in every lookup request

The device SHALL include an `appVariant` field in every `POST /lookup` request body.

#### Scenario: Christian build sends christian variant

- **WHEN** a Christian build initiates a lookup
- **THEN** the request body SHALL include `appVariant: "christian"`

### Requirement: Backend dispatches by appVariant to a registered adapter

The backend SHALL look up the adapter for the incoming `appVariant` and call its `select` method.

#### Scenario: Known variant dispatches to adapter

- **WHEN** the request `appVariant` is `"christian"` or `"stoic"`
- **THEN** the backend SHALL route the request to the registered adapter for that variant

#### Scenario: Unknown variant is rejected

- **WHEN** the request `appVariant` is any other value
- **THEN** the backend SHALL return `400` with `{ error: { code: "unknown_variant", message } }`

### Requirement: Stoic adapter returns a not-implemented stub

The Stoic adapter SHALL exist, be registered, and return a clear not-implemented payload until the Stoic corpus is seeded.

#### Scenario: Stoic request returns stub

- **WHEN** the backend receives a valid request with `appVariant: "stoic"`
- **THEN** the backend SHALL return `200 OK` with `{ status: "not_implemented", appVariant: "stoic", message }`
- **AND** the response SHALL NOT contain `primary` or `alternates`

### Requirement: Adapter contract is variant-agnostic

Every adapter SHALL implement the same Protocol: `app_variant: str` and `async select(req: LookupRequest) -> LookupResult`.

#### Scenario: Adding a new variant

- **WHEN** a new adapter class is added that implements the Protocol and is registered in the variant table
- **THEN** the backend SHALL serve requests for that variant without changes to the HTTP layer

### Requirement: Device results screen branches on appVariant

The device results screen SHALL branch its presentation copy on the build's `appVariant`.

#### Scenario: Christian build labels the response as a Bible verse

- **WHEN** the device renders results for a Christian build
- **THEN** UI copy SHALL refer to the primary item as a "verse" or "Bible verse" (e.g. heading "A verse for you")
- **AND** the results SHALL display the translation name returned by the backend
