## ADDED Requirements

### Requirement: Backend owns an approved Dhammapada catalog

The backend SHALL store an approved Dhammapada catalog containing canonical passage text and retrieval metadata for every passage eligible for lookup.

#### Scenario: Catalog entry contains canonical and retrieval fields

- **WHEN** a catalog entry is loaded
- **THEN** it SHALL include a stable `id`, `passageRef`, `displayLabel`, canonical `text`, translator/source/license metadata, `themes`, `useWhen`, `avoidWhen`, `tone`, `summary`, `emotionalFit`, `couldThisSoundBlaming`, `vulnerableStatesToAvoid`, and `riskNotes`
- **AND** retrieval metadata SHALL be stored separately from canonical passage text

#### Scenario: Catalog validation rejects incomplete provenance

- **WHEN** a catalog entry is missing translator, source URL, public-domain status, or license note
- **THEN** catalog validation SHALL fail before the backend serves the catalog

### Requirement: Catalog labels are generated with LLM assistance and human review

The Dhammapada catalog labeling process SHALL use LLM-assisted first-pass metadata generation under a human-defined rubric, followed by validation and human review for high-risk labels.

#### Scenario: LLM generates first-pass retrieval metadata

- **WHEN** an approved canonical Dhammapada passage is sent through the labeling workflow
- **THEN** the labeling LLM SHALL return structured metadata matching the approved schema
- **AND** the metadata SHALL include themes, use-when guidance, avoid-when guidance, tone, summary, emotional fit, whether the passage could sound blaming, vulnerable states to avoid, and risk notes
- **AND** the metadata SHALL NOT modify canonical passage text

#### Scenario: Labeling separates semantic fit from safety and tone

- **WHEN** labels are generated for an approved passage
- **THEN** the labeling workflow SHALL produce semantic labels such as themes, summary, emotional fit, and use-when guidance
- **AND** it SHALL separately produce safety/tone labels such as tone, avoid-when guidance, whether the passage could sound blaming, vulnerable states to avoid, and risk notes

#### Scenario: Generated labels use unapproved vocabulary

- **WHEN** generated labels contain out-of-vocabulary themes, tones, emotional-fit values, or vulnerable-state values
- **THEN** catalog validation SHALL fail or require normalization before the labels are accepted

#### Scenario: High-risk labels require human review

- **WHEN** generated metadata references shame, grief, panic, despair, self-blame, abuse, betrayal, harm by another person, or crisis-adjacent language
- **THEN** those labels SHALL be marked for human review before the catalog is considered ready for lookup

#### Scenario: Fixture testing reveals poor matching

- **WHEN** fixture lookup review shows systematic poor matches or unsafe tone
- **THEN** the labeling rubric SHALL be revised
- **AND** affected labels SHALL be regenerated or reviewed before release

### Requirement: Labeling provider and model are selected during offline data preparation

The Dhammapada labeling workflow SHALL choose the labeling provider and model during an offline data-prep phase, separate from runtime lookup provider selection.

#### Scenario: Candidate labeling providers are evaluated

- **WHEN** the project is ready to label the Dhammapada catalog
- **THEN** the labeling workflow SHALL evaluate candidate models from Hugging Face, Fireworks, and Replicate when available credits make those platforms practical
- **AND** the workflow SHALL compare total estimated batch cost, JSON validity, schema/vocabulary compliance, label usefulness, tone judgment, latency, and retry behavior

#### Scenario: Labeling model differs from runtime lookup model

- **WHEN** a stronger, slower, or provider-specific model is chosen for offline labeling
- **THEN** runtime lookup SHALL NOT be required to use the same provider or model
- **AND** runtime lookup SHALL continue to optimize for per-request speed, cost, and reliable selection from the approved catalog index

#### Scenario: Full corpus labeling is not run before provider selection

- **WHEN** provider/model choice has not yet been made
- **THEN** the workflow SHALL run a representative sample of passages before labeling all approved passages
- **AND** the chosen provider, model, prompt version, and selection rationale SHALL be recorded with the labeled catalog outputs

### Requirement: LLM selects Dhammapada IDs from an approved index

The Dhammapada adapter SHALL provide the LLM with an approved compact catalog index and require the LLM to select passage IDs from that index only.

#### Scenario: Valid Dhammapada selection

- **WHEN** the adapter receives anonymized text, sentiment, emotions, and confidence
- **THEN** it SHALL ask the LLM to return exactly one primary passage ID and exactly two alternate passage IDs
- **AND** each selected ID SHALL come from the approved catalog index
- **AND** each selected item SHALL include a `shortReason` of 1-3 sentences

#### Scenario: LLM returns a nonexistent ID

- **WHEN** the LLM response contains an ID that is not present in the approved catalog
- **THEN** the adapter SHALL reject the response as malformed
- **AND** the backend SHALL NOT return LLM-generated passage text as a fallback

#### Scenario: LLM returns duplicate IDs

- **WHEN** the LLM response repeats the same ID for primary or alternates
- **THEN** the adapter SHALL reject the response as malformed

### Requirement: Backend fetches canonical Dhammapada text by ID

The backend SHALL return canonical Dhammapada text only by fetching it from the approved catalog after ID validation.

#### Scenario: Valid selected IDs are enriched

- **WHEN** the LLM returns valid Dhammapada IDs
- **THEN** the adapter SHALL fetch each selected passage from the backend catalog
- **AND** the response SHALL include canonical `text`, `ref`, `translation`, and `shortReason` for the primary and alternates

#### Scenario: LLM includes canonical-looking passage text

- **WHEN** the LLM includes quoted or extended Dhammapada text in `shortReason` or any unexpected field
- **THEN** the adapter SHALL reject or strip that text
- **AND** the backend SHALL only return canonical text fetched from the catalog

### Requirement: Dhammapada tone guardrails are enforced during selection

The Dhammapada selection prompt and metadata SHALL prevent harsh or moralizing passages from being selected for vulnerable user states.

#### Scenario: Vulnerable state avoids stern passages

- **WHEN** the anonymized text or emotion metadata indicates shame, grief, panic, despair, or self-blame
- **THEN** the selector SHALL prefer gentle or contemplative passages
- **AND** it SHALL avoid passages whose `tone` or `avoidWhen` metadata conflicts with that vulnerable state

#### Scenario: Direct passage can be selected for non-vulnerable reactivity

- **WHEN** the anonymized text indicates anger, reactivity, craving, or speech regret without acute shame, panic, despair, or self-blame
- **THEN** the selector MAY choose a direct passage if its metadata fits the situation

### Requirement: Dhammapada lookup does not require vector search

The initial Dhammapada lookup flow SHALL use curated catalog selection and SHALL NOT require Qdrant or another vector database.

#### Scenario: Initial corpus is small

- **WHEN** the approved catalog is limited to the Dhammapada corpus or a curated subset of it
- **THEN** the backend SHALL use a compact catalog index or deterministic shortlist for selection
- **AND** no vector database SHALL be required to serve lookups
