# Epic 7 — progress in backend/API scope

## 7.1 Contract and regression CI

- Generator API inventory guard locks all 12 operation IDs, shared JWT security/error responses, and consistency of description limits across OpenAPI, domain validation, and Analytics DDL.
- Analytics API inventory guard locks all 65 canonical operation IDs, OpenAPI version, and shared JWT security.
- Infra CI now semantically validates all four checked-in OpenAPI 3.1 documents and additionally checks unique operation IDs, expected inventory (107 operations total), local references, and success responses. The legacy Analytics draft intentionally has no global security; active contracts retain their existing JWT guards.
- Both service CI workflows already run Maven verification; this executes their contract guards, PostgreSQL migration-upgrade tests, and service acceptance/regression suites.
- Generated Web-client compatibility remains with the Web owner and is intentionally not changed here. 7.1 remains open until that compatibility check is supplied by the Web owner.

## 7.3 Failure and recovery verification

- Generator PostgreSQL acceptance proves an expired run lease transfers to a replacement worker without changing the durable attempt identity.
- Generator sink integration proves identical retry is idempotent, conflicting payload under the same batch identity is rejected, and invalid batches roll back header/measurements/hints atomically.
- Analytics migration upgrade and recalculation golden tests run in the existing CI suite. The golden test now restages a durable projection generation after a simulated worker restart before publication and asserts replacement is idempotent and unpublished metrics stay unchanged.
- Infra's monitoring-isolation smoke test stops Prometheus and Grafana in turn and checks both business services remain ready, expose metrics, and authenticate. It is part of `scripts/validate.sh` CI; the full Compose smoke was not rerun in this implementation pass.
- Remaining integrated fault-injection evidence: stop during an in-flight batch. Backup/restore drill stays deferred with Epic 1.5 per the explicit product decision; it is not counted complete here.

## 7.2 and 7.4 boundary

The numerical 4 vCPU/8 GB workload benchmark and clean-stack demo rehearsal are not recorded as complete: they require the integrated deployment, Web client, dashboards, and measured resource evidence. This work stays within the agreed backend, infra-code, Analytics, Generator, and API-contract boundary; it does not modify Web or execute deployment procedures.

## Verification run

- Infra OpenAPI validation: all four documents passed semantic OpenAPI 3.1 validation and structural inventory checks (107 operations total).
- Analytics `TelemetryGoldenSliceTest`: 2 tests passed, including the durable-stage restart/republication case.
- Generator full clean suite: 41 tests passed, including run control, recovery, migration application, and OpenAPI inventory guard.
- Analytics API operation inventory guard: 1 test passed.
- Analytics full clean suite: 76 tests passed, including the Analytics operation inventory guard.
