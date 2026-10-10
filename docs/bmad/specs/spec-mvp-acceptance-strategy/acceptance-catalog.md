# Acceptance catalog

This catalog describes observable outcomes. Field-level schema constraints and complete operation shapes remain in the Analytics, Generator, and Auth OpenAPI contracts. Contract tests must enumerate every `operationId`; the scenarios below exercise meaningful combinations across those operations.

## AC-1 — Configure enterprise and equipment

**Given** an authenticated initial operator and an empty application database, **when** the operator creates an enterprise with IANA timezone and two non-overlapping local shift definitions, creates a line, creates one machine directly on that line and another unassigned, then batch-assigns the unassigned machine to the same enterprise's line, **then** all objects have stable IDs and `ACTIVE` status, the second assignment succeeds once, cross-enterprise assignment is rejected without partial changes, and the resulting tree exposes components/signals only under their owning machine. A second attempt to move an already assigned machine returns a conflict. Disabling a parent does not cascade the child's stored status, but readiness checks and new Generator starts reject disabled required parents. Historical reads by known IDs remain possible.

**Trace:** equipment creation/assignment/status operations in Analytics OpenAPI; Enterprise, ProductionLine, Machine and Component specs.

## AC-2 — Rules, event-time state and delayed evaluation

**Given** a ready active machine with a numeric speed signal and an active state rule (`RUN` when speed `>= 100`, activation delay 3 s; release below 70 for 5 s), **when** a usable value 120 is observed at `12:00:00Z`, **then** the RUN interval has `effectiveFrom=12:00:03Z`, even if a worker detects/publishes it at `12:00:08Z`; `detectedAt` reports the latter separately. If value 60 is observed at `12:00:10Z`, the transition to IDLE is effective at `12:00:15Z`. A value equal to 70 does not satisfy strict `<70` release. A data-quality-invalid sample does not count as a usable rule input. If signal freshness/offline deadlines elapse without a new sample, the deadline worker produces the corresponding state at the configured event-time boundary.

**Trace:** StateRule operations, machine current-state read, evaluation deadlines; machine-state rules and projection specs.

## AC-3 — Numeric metric formulas and rollup aggregation

**Given** one machine over a 60-minute selected interval with RUN 30 min, IDLE 15 min, DOWN 10 min, SETUP 5 min, no planned stop/offline, nominal rate 100 pcs/hour, output 50, scrap 5 and failures 2, **when** the closed-minute projection is queried, **then** planned production time is 60 min, operating time 45 min, availability 0.75, ideal output 75, performance 50/75 (0.6667), quality 45/50 (0.90), OEE 0.45, MTBF 22.5 min, and MTTR 5 min. PLANNED_STOP is excluded from planned production time; OFFLINE contributes a data gap/coverage reduction, not DOWN. Multi-machine ratios are recomputed from summed numerators and denominators, never by averaging machine percentages. Incompatible production units yield `null` production ratios, not a fabricated conversion.

**Trace:** metric query operations; metric catalog and `numeric-examples.md`.

## AC-4 — Late telemetry and atomic recalculation publication

**Given** a committed projection and an accepted raw batch whose event time is behind `dataThrough`, **when** the late batch is ingested, **then** raw rows remain append-only, affected UTC minute windows are marked dirty, and the current/history query may return the previous complete projection with its prior `dataThrough` plus stale/recalculating metadata. The worker reconstructs context from the preceding stable boundary, stages replacement intervals and rollups, and publishes the complete affected range in one short transaction. A reader during staging sees the old committed projection; after publication it sees the new projection, never a partial mixture. Retrying the same batch ID/hash has no duplicate effect; reusing the ID with a different hash conflicts.

**Trace:** telemetry batch persistence contract, recalculation/job operations, current/history query operations; raw ingestion, projection-storage and idempotency specs.

## AC-5 — Recalculation range and rules

**Given** a state-rule change, **when** it is saved, **then** past history does not silently change. The user can request an explicit `PERIOD` or `ALL` recalculation; its worker uses the current rule configuration for the selected replay, exposes durable job status/progress, and atomically replaces affected output. A no-op/duplicate retry does not add durations or counts a second time. Invalid or out-of-retention ranges fail before work is scheduled.

**Trace:** rules and recalculation API operations; recalculation-process and transaction-idempotency specs.

## AC-6 — Manual incident and idempotency

**Given** an authenticated user and an eligible machine/time range, **when** the user creates a manual incident with an `Idempotency-Key`, **then** the incident is durable and affected loss projections are marked for asynchronous recalculation. Repeating the same key and same request returns the original result; the same key with a different request returns conflict. Invalid ownership, forbidden state/reason overlap, and non-eligible reason ranges return a validation/conflict response without partial writes. SETUP/PLANNED_STOP state effects and loss-reason effects follow the separate overlap rules in the incident spec; raw telemetry is never edited.

**Trace:** ManualIncident/LossReason operations; loss-reasons-incidents and transaction-idempotency specs.

## AC-7 — Current and historical frontend reads

**Given** the Web client has selected an enterprise/line/machine and a `shiftId`, **when** it requests current/overview data, **then** the response includes the requested scope, units/metric metadata, `dataThrough`, calculation time, stale/recalculating signals and available values without forcing synchronous recalculation. Historical requests use aligned closed UTC-minute data and state actual returned bounds, selected `shiftId`, timezone/shift-date context, bucket size and truncation/coverage metadata. Empty ranges return a valid empty result; partial coverage is represented explicitly. Query limits (period and point ceilings) produce documented client errors instead of unbounded reads.

**Trace:** current/overview/timeseries/Pareto/chronometry operations; analytics-query, shift-calendar, metric-formulas and Analytics OpenAPI specs.

## AC-8 — Realtime generation

**Given** an active validated scenario referencing ready equipment and signals, **when** an authenticated user starts an immediate realtime run, **then** the run captures an immutable expanded behavior/equipment snapshot and deterministic seed, reserves its machines atomically, emits raw samples using wall-clock event timestamps and bounded JDBC batches, and skips overdue ticks rather than catch-up bursting. Another overlapping realtime run for the same machine is rejected. `COMPLETED` means raw generation completed; Analytics projection freshness is queried separately. A retryable failure can be explicitly retried from its checkpoint using the same run identity and stable batch IDs.

**Trace:** Scenario and Run operations; Generator API, run execution, concurrency and telemetry writer specs.

## AC-9 — Historical and future scheduled generation

**Given** a valid scenario, **when** a historical run is requested for an allowed range, **then** virtual event time covers the requested half-open range, processing is checkpointed in five-minute chunks, deterministic batch IDs make retries safe, and historical capacity is limited/throttled to protect realtime reads/writes. When a run is scheduled for a future UTC instant, **then** it emits no raw rows before that instant; it starts at due time with wall-clock event time, and if the scheduler misses the allowed 30-second window it ends as `SCHEDULE_MISSED` rather than backfilling unexpectedly. A repeated/overlapping reserved machine range is rejected before partial reservation.

**Trace:** Generator scheduling/history Run operations; execution modes, checkpoints and concurrency specs.

## AC-10 — Auth, errors and traceability

**Given** an unauthenticated or malformed request, **when** it reaches a protected operation, **then** it returns the documented 401/400/404/409/422/429/5xx shape as applicable and contains a request trace identifier; successful and error responses expose `X-Trace-Id`. Invalid/expired JWTs are rejected by both business APIs. Passwords, bearer tokens, JWT signing secrets, database credentials and raw measurement values never appear in logs. Each OpenAPI operation is checked for required security, parameters, success schema, documented common errors and trace behavior according to its contract.

**Trace:** Auth, Analytics and Generator OpenAPI contracts; security-audit and observability specs.

## AC-11 — Configuration and database integrity

**Given** a clean supported PostgreSQL instance, **when** the Analytics Liquibase changelog is applied once and application starts, **then** all owned schemas and constraints exist, `equipment.schema_release` matches the supported release, and Generator starts only after that readiness check. Reapplying migrations is safe. Invalid FK ownership, cycles in component parentage, duplicate scoped stable codes, invalid shift overlap and conflicting idempotency keys fail atomically. Existing Flyway bootstrap metadata is preserved and is not treated as domain data or automatically deleted.

**Trace:** Liquibase/schema specs and equipment, telemetry, projection, incident, generator table specs.
