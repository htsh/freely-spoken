# Security Policy

## Supported Versions

This repository is maintained from the `main` branch.

## Reporting a Vulnerability

Please do not open a public issue with secrets, personal data, recordings, raw transcripts, private deployment details, or exploit instructions.

For security reports or privacy-sensitive issues, use GitHub's private vulnerability reporting flow for this repository if it is available. If private reporting is not available, open a minimal public issue that asks for a private contact path and does not include sensitive details.

Useful reports include:

- what behavior you observed
- the affected app, backend endpoint, or tool
- reproduction steps using non-sensitive sample data
- whether any data beyond the anonymized lookup payload could leave the device

## Privacy Boundary

The intended privacy boundary is documented in [README.md](README.md) and [docs/privacy-policy.md](docs/privacy-policy.md). In short: audio and raw transcripts should stay on device; the backend should receive only the reviewed anonymized summary, sentiment metadata, confidence score, and app variant.
