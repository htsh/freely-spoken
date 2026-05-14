## ADDED Requirements

### Requirement: FastAPI app boots on localhost:8000

The harness SHALL be a FastAPI application that starts an HTTP server on port 8000.

#### Scenario: Server starts successfully

- **WHEN** the user runs the FastAPI entrypoint
- **THEN** the server SHALL listen on `http://localhost:8000` and respond to HTTP requests

### Requirement: Index page renders sample picker

GET `/` SHALL render an HTML page containing a list of sample inputs, a variant toggle, and a run button.

#### Scenario: Loading the index page

- **WHEN** the user navigates to `/`
- **THEN** the page SHALL display all samples from `fixtures/samples.json`
- **AND** the page SHALL include a toggle between "Christian" and "Stoic" variants
- **AND** the page SHALL include a free-form text input for ad-hoc inputs
- **AND** the page SHALL include a run button

### Requirement: Run endpoint executes the pipeline

POST `/run` SHALL accept a sample selection and variant, execute the sentiment pipeline, and render results.

#### Scenario: Running a sample through the pipeline

- **WHEN** the user selects a sample and clicks run
- **THEN** the system SHALL call the Swift CLI subprocess with the sample text
- **AND** the system SHALL display the result page with sentiment fields and LLM output

#### Scenario: Running ad-hoc text

- **WHEN** the user enters free-form text and clicks run
- **THEN** the system SHALL process the text through the same pipeline as fixture samples

### Requirement: Result page displays all pipeline output

The result template SHALL display every field produced by the pipeline.

#### Scenario: Viewing a complete result

- **WHEN** a run completes successfully
- **THEN** the result page SHALL show: original text, anonymized text, sentiment, emotions, confidence, raw model output (collapsible), strategy badge, LLM verse references, and crisis banner if flagged
