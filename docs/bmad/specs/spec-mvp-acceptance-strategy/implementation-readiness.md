# Implementation readiness

## Entry decision

**Analytics phase: ready to decompose and implement once this planning package is committed and the readiness checklist below is satisfied.** This is not a claim that services, migrations, CI or performance tests have already been implemented or passed.

## Authoritative inputs

- Product boundary and demo scenario: `../spec-mvp-scope/`.
- Cross-service boundaries, deployment and shared database: `../../architecture/fkit-bi-architecture.md`, `../../architecture/fkit-bi-components.md`, and `../spec-analytics-modules/`.
- Equipment/time/rules/telemetry/state/rollups/metrics/incidents: the corresponding `spec-equipment-*`, `spec-shift-calendar`, `spec-machine-state-*`, `spec-raw-telemetry-ingestion`, `spec-minute-rollups`, `spec-metric-formulas`, `spec-timeseries-pareto-chronometry`, and `spec-loss-reasons-incidents` packages.
- Public contracts: `fkit-bi-analytics/docs/contracts/analytics-api-draft.yaml`, `fkit-bi-generator/docs/contracts/generator-api-draft.yaml`, `fkit-bi-infra/docs/contracts/auth-api.yaml`; despite historical `draft` filenames, current v1 schemas are normative as declared by their contract specs.
- SQL/migrations and runtime: `spec-sql-equipment-foundation/`, `spec-analytics-projection-storage/`, `spec-transaction-idempotency/`, `spec-concurrency/`, `spec-observability-runtime/`, `spec-security-audit/`, `spec-mvp-load-slo/`.
- Executable verification: `acceptance-catalog.md` and `test-strategy.md` in this package.

## Decisions explicitly closed for MVP

- One PostgreSQL database; two separately deployable Spring applications with Analytics owning Liquibase and shared SQL contracts.
- Equipment hierarchy Enterprise → line(s), Enterprise → machine(s), Machine → component tree/signals; machines may initially be unassigned and later assigned once; statuses remain only ACTIVE/DISABLED.
- Raw measurements are append-only and primarily optimized for bounded batch writes and time-range retrieval; event-time projections/rollups serve frontend reads.
- Analytics runs continuously in background workers; clients synchronously read the latest committed projection and see lag/stale/recalculation metadata.
- Generator supports realtime, bounded historical replay and one-time future scheduled runs; behavior correction of individual nodes is future work.
- Shift is enterprise-defined and every applicable request carries `shiftId`; explicit shift boundaries and local-time/DST policy are in the shift spec.
- Config changes do not silently rewrite history; user-requested period/all recalculation uses current rules and atomically replaces the selected projection.
- Manual incident is the only incident creation path in MVP; no automatic classification. JWT authentication is mandatory, without general roles/RBAC. Bootstrap operator can add users.
- Analytics and Generator APIs are separately versioned; monitoring requires Prometheus/Grafana and Nginx/TLS deployment options.
- Overload may drop raw telemetry only under the explicit observable policy; configuration, incidents and published projection integrity do not use that loss policy.

## Readiness checklist

- [x] Domain decisions are in block specs, with known exclusions visible.
- [x] SQL ownership, migration owner, persistence approach, transaction seams and idempotency are specified.
- [x] Analytics, Generator and Auth v1 API documents exist and contract validation has been recorded in their specs.
- [x] User flows for setup, current reads, historical analytics, manual incidents and all run modes are described.
- [x] Formula, state, event-time, late-data and scheduling examples are executable acceptance inputs.
- [x] Test layers and measurable verification gates are stated without claiming they ran.
- [x] Cross-document conflicts found in TODO and analysis notes have been corrected; architecture spine is aligned to current contracts.
- [x] Epics/stories are decomposed into implementation-sized outcomes and mapped to owning repositories/modules.
- [x] Backup, raw partition cleanup and structured-log/correlation decisions have an owner and an MVP operating policy.
- [x] Dirty planning changes are committed before implementation work begins.
- [ ] Implementation CI, PostgreSQL migration tests, load benchmark, backup restore drill, deployment/TLS validation pass. These are implementation/release gates, not analytics design blockers.

## Implementation boundary

Start with one vertical slice from empty PostgreSQL to a valid authenticated equipment configuration and generated realtime telemetry, then add projection/current read, historical replay, manual incidents, and operational hardening. Avoid beginning with broad CRUD scaffolding disconnected from an end-to-end acceptance path. Do not mark this design package as implementation-complete until the unchecked runtime gates have evidence.
