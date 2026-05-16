# Pre-Deployment VPS Load Stage for `/lookup` (k6)

## Summary

- Add a manual, ad-hoc pre-deployment load stage that hits the live VPS endpoint directly and measures how many `/lookup` calls it can sustain before quality breaks.
- Use a 3-phase gated ladder: `1h discovery` -> `6h soak` -> `24h soak`.
- Define break as sustained error-rate degradation, then run soaks at a safe fraction of discovered throughput.
- Measure "free calls" primarily as successful client calls to `/lookup`, while also reporting fallback/retry amplification from response metadata.

## Approach

- Chosen: k6 black-box stage from a separate macOS runner, using only client-observed latency/error metrics plus artifact exports.
- Alternative 1: custom Python async runner. More custom logic, less standard load tooling.
- Alternative 2: Locust. Strong but heavier setup than needed for this stage.
- Why chosen: fastest path to repeatable ramp + soak scenarios with consistent thresholds and machine-readable outputs.

## Implementation Changes

- Add `tools/load-test/` with:
- A k6 script for `/lookup` that sends Christian payloads and headers from env vars.
- A run orchestrator (shell or Node wrapper) that executes phases sequentially with gate logic.
- A fixture corpus file with `1000+` unique anonymized payloads.
- A results summarizer that emits artifacts per phase.
- Add docs for setup/run in a pre-deploy guide under `docs/`.

### Request Fixture Interface (New)

- Each fixture item contains: `anonymizedText`, `sentiment`, `emotions[]`, `confidence`.
- Runtime request body adds fixed `appVariant: "christian"`.

### Runtime Inputs (New)

- `LOOKUP_STAGE_URL`, `LOOKUP_STAGE_SECRET` from environment variables.
- `LOAD_SEED` for deterministic randomization/replay.
- Phase-specific knobs (duration, target rate, caps) with defaults below.

### Smoke Test (pre-phase)

Before starting the 3-phase ladder, run a short validation step:
- Send 10 requests with random fixtures from the corpus.
- Verify all return HTTP 200 and contain valid JSON with `primary.ref`.
- Verify auth header (`LOOKUP_STAGE_SECRET`) is accepted (not 401/403).
- Verify fixture corpus loads and `LOAD_SEED` produces deterministic request bodies.
- If any check fails, abort immediately with a clear error — do not proceed to Discovery.

### Phase Logic (New)

- Discovery (1h): aggressive linear ramp, `+2 RPS every 5 min`, break on sustained `>5%` non-2xx over rolling 5-minute window, stop immediately on break, cap `5,000` calls.
- If no break occurs, use highest stable RPS reached as discovered capacity.
- Soak 6h: run at `75%` of discovered stable RPS, pass if `<1%` errors and `p95 < 8s`, cap `20,000`.
- Soak 24h: same thresholds, cap `50,000`.
- Progression is gated: 24h only runs if discovery and 6h pass.
- If a soak hits call cap before duration completes, mark Inconclusive (not pass/fail).

### Artifacts (New)

- `summary.json` with pass/fail/inconclusive, discovered RPS, safe RPS, totals, error rates, latency percentiles.
- `timeline.csv` with interval metrics (requests, errors, p50/p95/p99, status buckets).
- `sample-errors.jsonl` with bounded sampled failures (no full response dump for every request).

## Test Plan

- Local smoke test of the runner against a local backend target to validate wiring, headers, seed behavior, and artifact generation.
- Discovery-phase validation: confirm early abort when threshold breaches and stable-RPS calculation when it does not.
- 6h soak validation: confirm pass/fail gates and threshold enforcement.
- 24h soak validation: confirm gated execution and inconclusive classification on cap hit.
- Replay validation: rerun with same `LOAD_SEED` and verify request-sequence determinism.

## Assumptions and Defaults

- Target is the live VPS endpoint (not a separate staging service).
- Christian variant only; deployed provider chain used as-is.
- Server cache remains ON (measure real production behavior).
- Runner is a separate macOS machine.
- Stage is manual/ad-hoc, not CI-enforced initially.
- Client-side observability only (no required `fly logs` correlation for v1).
