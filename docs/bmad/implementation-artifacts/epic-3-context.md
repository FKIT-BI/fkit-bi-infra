# Epic 3 Context: Reliable raw telemetry and realtime state

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Persist valid realtime measurements quickly and reliably, then make current signal values and machine state available from prepared projections. The design separates telemetry ingestion, asynchronous calculation, and reads so frontend queries do not wait for processing or scan raw history; bounded degradation and explicit currency/freshness metadata keep the system useful under load.

## Stories

- Story 3.1: Raw schema and partition lifecycle
- Story 3.2: Telemetry writer
- Story 3.3: Ingestion-to-work handoff
- Story 3.4: Signal current projection
- Story 3.5: State evaluation and deadlines
- Story 3.6: Realtime golden slice

## Requirements & Constraints

- Preserve raw measurements as append-only typed records. Enforce packet-level idempotency and validate signal/configuration semantics before writing; avoid per-measurement foreign keys, unique constraints, and indexes on value payloads.
- Keep each batch atomic and short (1–1000 measurements). Persist batch identity/hash, raw rows, first-use signal markers, and durable recalculation hints together.
- Partition raw data by UTC day of `observed_at`, maintain the active retention window plus seven future days, and keep partition DDL/retention work outside ingestion transactions. Retention must not remove data needed by pending work or active calculation/publication.
- Validate event timestamps, clock skew, quality, and configured value bounds. Preserve uncertain/bad and out-of-range observations for visibility while excluding them from usable current values.
- Use bounded retry/buffering and observable telemetry loss rather than allowing a stalled writer to block the service indefinitely. Realtime ingestion and query capacity must not be starved by historical work.
- Expose current reads from committed projections only, including last received/usable values, freshness/quality, and calculation currency (`dataThrough`, `calculatedAt`, stale/recalculating state).
- System `OFFLINE` takes precedence when no accepted machine telemetry arrives within `offlineAfterMs` (60-second MVP default). Signal freshness is independently `NO_DATA`, `FRESH`, or `STALE`; stale rule inputs evaluate as unknown.
- State evaluation must support priority, typed conditions, activation/release delays, hysteresis, and default state. Distinguish event-effective time from worker detection time; maintain one nearest evaluation deadline per machine.
- The golden slice must demonstrate configured equipment → generated batch → persisted measurements → current signal/state reads and satisfy the roadmap acceptance criteria without query-time raw scans.

## Technical Decisions

- Analytics owns Liquibase DDL and projection/schema changes; Generator owns execution and writes only through the shared, versioned telemetry append contract. Both applications use separate internal modules/adapters with ports-and-adapters boundaries and one PostgreSQL integration boundary.
- Batch identity is `(producer_id, producer_batch_id)` with SHA-256 of the exact versioned `TELEMETRY_BATCH_V1` encoding. Matching retries succeed idempotently; reusing an identity with a different hash is a conflict.
- Raw rows contain exactly one typed value. Shared physical encodings: mode `1=REALTIME`, `2=HISTORICAL`; source quality `0=GOOD`, `1=UNCERTAIN`, `2=BAD`; validation flags `1=OUT_OF_RANGE`, `2=CLOCK_SKEW`. Keep quality separate from flags.
- Use UTC-day RANGE partitions without a default partition and local `(signal_id, observed_at)` index. Raw retention is 90 days by PostgreSQL time. Partition creation/retirement uses guarded routines, topology coordination, short lock timeouts, and retry outside the hot path.
- The durable handoff is database-backed: discover accepted batches in order, coalesce affected ranges by machine/event time, and checkpoint/lease work. Workers use `FOR UPDATE SKIP LOCKED` to distribute independent machine work; crashes permit retry.
- Current projections are replaced/published atomically after computation. Readers see either the previous or new committed projection; late/historical input causes bounded replay rather than incremental double-counting. Calculation/read paths reserve capacity independently from ingestion.
- Store one current state configuration per machine, validated and compiled to a typed runtime model. Persist one nearest deadline per machine; worker leases and `SKIP LOCKED` drive delayed transitions without an external broker.

## Cross-Story Dependencies

- Story 3.1 defines the shared raw schema and versioned write contract required by Stories 3.2–3.3 and the Analytics projections in 3.4–3.5.
- Story 3.2 must atomically create the durable handoff consumed by Story 3.3; the handoff must identify the event-time ranges that Stories 3.4–3.5 recalculate.
- Story 3.4 signal-current/freshness semantics supply inputs to Story 3.5 state evaluation and deadline scheduling.
- Story 3.6 integrates configured equipment from Epic 2 with Generator writing and Analytics projections; the two services must support the same schema release and telemetry contract.
