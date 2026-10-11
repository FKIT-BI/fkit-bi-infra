# Epic 5 Context: Manual incidents and loss attribution

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Allow operators to record business context for machine losses and see that context reflected in refreshed analysis, without changing raw telemetry or calculated state history. Manual classifications must remain deterministic, explainable, and compatible with asynchronous projection recalculation.

## Stories

- Story 5.1: Loss reason catalog
- Story 5.2: Manual incident lifecycle
- Story 5.3: Loss projections and UI reads
- Story 5.4: Incident golden tests

## Requirements & Constraints

- Loss reasons belong to an enterprise, have a stable enterprise-unique code, a closed category, and ACTIVE/DISABLED lifecycle. Disabling a reason prevents new assignment but does not invalidate existing history; physical deletion is not supported.
- One manual incident may set a state override, a loss reason, or both. At least one effect is required. Intervals are half-open UTC ranges; an open-ended interval continues until closed. Future boundaries are not allowed.
- At any instant there may be at most one active state override and one active reason per machine. These dimensions are checked independently, so a state-only incident may overlap a reason-only incident. Conflicts must be rejected explicitly.
- Reasons apply only to effective `IDLE`, `DOWN`, `SETUP`, or `PLANNED_STOP` time. They do not classify `RUN` or `OFFLINE`, and must not alter underlying signal quality or calculated state. Unclassified loss remains representable.
- Mutations must be idempotent where retried, including close and cancellation. Cancellation is soft and preserves the incident record. Validate ownership and eligible loss coverage; a reason-only incident with no eligible interval is rejected.
- Recalculation is asynchronous. Until refreshed projections commit, reads may return the previous complete result with freshness/recalculating information. Acceptance must cover incident behavior, projection refresh, and AC-6 including a lost-response retry.

## Technical Decisions

- Keep manual intent separate from append-only raw telemetry and calculated state intervals. Derive effective state and attributed loss from calculated intervals plus active manual incidents; do not rewrite source facts.
- Model user-defined reasons as enterprise-scoped records, not enum values. `LossCategory` is a closed application/API enum stored as validated text with a database constraint. Reason identity, enterprise, and code are stable; category becomes immutable after first use.
- Use one ManualIncident model with conditional `stateOverride` and `lossReasonId`; derive its effect type rather than persisting a redundant type. Preserve cancelled rows for history.
- Each incident mutation atomically records durable recalculation work for the minute-aligned union of its previous and new interval. Rebuild and publish effective-state intervals, machine metric buckets, and machine loss buckets together using retry-safe replacement semantics. Do not mutate raw telemetry, signal rollups, or calculated state intervals.
- Effective intervals retain both calculated and effective state, source, and incident/reason references so manual attribution remains explainable after state-rule replay.

## Cross-Story Dependencies

- Epic 3 provides raw telemetry, calculated state intervals, current state, and durable recalculation handoff. Epic 4 provides the historical projections, loss buckets, read/query patterns, and atomic publication foundation that incident mutations extend.
- Story 5.1 supplies the reason identities and category/status semantics used by incident validation and loss reads. Stories 5.2 and 5.3 depend on the same effective-state and loss projection publication path; Story 5.4 verifies the integrated behavior.
