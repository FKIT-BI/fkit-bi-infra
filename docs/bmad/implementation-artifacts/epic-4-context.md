# Epic 4 Context: Historical projections and query API

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Let the frontend read bounded, timely history, shift views, and production metrics from prepared Analytics projections. This turns accepted telemetry and calculated states into responsive operational and historical analysis while keeping query work independent from ingestion and long recalculations.

## Stories

- Story 4.1: Calculation queue and publication
- Story 4.2: Minute rollups
- Story 4.3: Metric calculator
- Story 4.4: Current and overview reads
- Story 4.5: Historical series/Pareto/chronometry
- Story 4.6: Explicit replay jobs
- Story 4.7: Late-data acceptance

## Requirements & Constraints

- Recalculate affected ranges for new, late, and historical data. Merge dirty windows by machine, align them to UTC minutes, include the evaluator context needed before the range, and calculate through the current complete-data boundary.
- Publish a fully validated replacement atomically. Readers must see either the prior committed result or the new one, never partial ranges. Keep raw telemetry append-only; use idempotent replace/upsert semantics rather than cumulative increments.
- Persist only the required one-minute projections: numeric signal aggregates, machine metric buckets, and machine loss buckets. Store additive facts (state durations, output/scrap, transition counts, numeric statistics and loss durations), not precomputed ratios. Build larger response buckets at read time.
- Calculate availability, performance, quality, OEE, MTBF, and MTTR from totals over the requested period. Never average ratios across buckets or machines. Treat OFFLINE as a data gap, PLANNED_STOP separately, and preserve defined loss denominators and null-reason grouping.
- Historical results use closed UTC-minute coverage and report actual bounds, `dataThrough`, calculation freshness, and stale/recalculating or empty/partial status as applicable. Do not query raw telemetry as a metric fallback or to fill incomplete range edges.
- Bound historical requests to the 90-day MVP window. Support aligned `AUTO|5m|15m|1h|1d` series; limit metric/loss series to 1,000 points and telemetry series to 720. Chronometry uses exact effective intervals and shift occurrence context.
- Query targets: current API p95 ≤500 ms, overview ≤1 s, analytics through 30 days ≤2 s and through 90 days ≤5 s. Under nominal load, current signal/state/rollup lag targets are 15/20/120 seconds. Benchmark evidence must confirm these targets.
- Raw retention is 90 days. Retention must not remove raw data needed by outstanding work or unpublished projections; historical input outside the active raw window is unavailable for recalculation.

## Technical Decisions

- Keep ingestion, calculation workers, and read API as separate paths. Ingestion commits durable work hints with accepted telemetry; workers read committed raw data without row locks; API reads only committed projections and freshness metadata.
- Merge per-machine dirty ranges and track discovery/execution with durable queue/checkpoint state. Long replay writes validated staging outside the publication transaction. A short transaction replaces the affected projection/state range and updates currency, checkpoints, and work/job status together.
- Workers are at-least-once and must be safe to retry. Use leases and PostgreSQL `SKIP LOCKED` for worker queues; no external broker or per-measurement jobs. Respect separate query and worker connection budgets so workers cannot consume the read pool.
- Preserve exact state-transition timestamps in interval history while published coverage is UTC-minute aligned and half-open. Rollups are additive facts; current hierarchy is used for enterprise/line aggregation.
- Explicit replay accepts PERIOD or ALL, uses current rules, validates the requested range, and exposes durable progress/status. Rule changes update current results; historical rules are not silently versioned or replayed automatically.

## UX & Interaction Patterns

- Reads return the latest committed projection without waiting for calculation. Include currency/freshness and recalculation status so the frontend can communicate lag while displaying usable prior results.
- Historical series expose selected/actual interval bounds, bucket size, units, coverage and truncation metadata. Shift analytics identify occurrences by `shiftId` and local `shiftDate`; optional `shiftId` narrows chronometry to one occurrence.
- Pareto responses group missing reasons as `UNCLASSIFIED` and the remaining tail as `OTHER`; chronometry returns exact state intervals without duplicating them as a reason grouping.

## Cross-Story Dependencies

- Epic 3 supplies the raw telemetry contract, current state/intervals, and durable dirty-work handoff that this epic recalculates and projects.
- Epic 5 incident changes feed dirty windows and consume refreshed effective/loss projections; manual classification must survive state-rule replay.
- Replay and late-data paths share the same staging and atomic replacement guarantees as ordinary queue publication.
