---
id: SPEC-mvp-acceptance-strategy
companions:
  - acceptance-catalog.md
  - test-strategy.md
  - implementation-readiness.md
  - implementation-roadmap.md
  - operations-decisions.md
  - operation-traceability.md
sources:
  - ../planning-artifacts/analytics-specification-todo.md
  - ../spec-mvp-scope/SPEC.md
  - ../spec-mvp-load-slo/SPEC.md
  - ../spec-metric-formulas/SPEC.md
  - ../spec-machine-state-projections/SPEC.md
  - ../spec-analytics-api-contract/SPEC.md
  - ../spec-generator-api-contract/SPEC.md
---

> **Canonical contract.** This SPEC and its companions define implementation acceptance, verification scope, and the gate before development starts. Referenced source specs remain authoritative for domain/API details.

# MVP acceptance and verification strategy

## Why

The project has enough accepted domain, persistence, analytics, generator, and API decisions to build, but those decisions need executable acceptance examples and a cross-cutting test plan. This package prevents implementation from silently changing event-time semantics, exposing partial recalculations, or claiming unverified throughput.

## Capabilities

- **CAP-1**
  - **intent:** A developer can determine whether each principal MVP user journey meets the accepted behavior.
  - **success:** The acceptance catalog covers equipment setup, telemetry-to-analytics, recalculation, incidents, current/historical reads, and realtime/history/future generation with explicit expected outcomes.
- **CAP-2**
  - **intent:** A developer can test domain behavior without a running service and verify PostgreSQL-specific behavior against PostgreSQL.
  - **success:** The test strategy separates pure unit/property tests, API contract tests, PostgreSQL integration tests, end-to-end golden tests, load tests, and recovery tests.
- **CAP-3**
  - **intent:** The team can establish implementation readiness without confusing a written plan with executed verification.
  - **success:** Readiness identifies the approved inputs and marks benchmark, restore drill, and CI execution as implementation-stage verification, not completed results.

## Constraints

- Accepted domain and OpenAPI specs are normative; this package adds acceptance evidence without redefining contracts.
- Time intervals use UTC instants and half-open `[from,to)` boundaries. Event time (`observedAt`) is distinct from ingest/detection time.
- Reads return the latest fully committed projection; recalculation publishes an entire affected range atomically.
- Service availability and current reads take precedence over full raw-data preservation during overload, as defined by the ingestion contract.
- MVP target host and workload/SLO values come from `spec-mvp-load-slo`; this package must not invent passing performance results.

## Non-goals

- Executing implementation tests, deploying services, or claiming benchmark results before code exists.
- Exhaustively documenting every field-level validation already specified by the OpenAPI schemas.
- Expanding MVP into RBAC, Kafka, automatic incident classification, multi-region HA, or a separate analytics database.

## Success signal

Before implementation starts, every accepted requirement maps to a model/API behavior and a planned verification; known exclusions and technical debt are explicit. During implementation, all required CI and benchmark gates pass or deviations are documented and accepted before release.

## Assumptions

- Existing draft OpenAPI paths are treated as final v1 contracts only where the corresponding final contract spec says so; file names containing `draft` do not make those decisions provisional.
- Every OpenAPI operation receives automated request/response/security/error-shape coverage; Given/When/Then scenarios are written at user-command/workflow level and link to all relevant `operationId`s to avoid duplicative prose.
- A local nightly backup is a demo-MVP recovery measure, not protection against host loss. An off-host copy is an operator/deployment responsibility if host-loss recovery is required.
