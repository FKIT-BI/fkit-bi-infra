# Test strategy

## Test layers

| Layer | Scope | Required evidence |
|---|---|---|
| Unit | Pure comparison/evaluator, timing/deadline rules, interval normalization, metric formulas, loss attribution, scenario compilation, run scheduling and state transitions | Deterministic tests with boundary cases; no Spring or database required |
| Property | Interval partitioning and conservation, rollup aggregation, idempotent replace, batch hashing, deterministic generation | Reproducible seed; invariants checked over generated inputs |
| PostgreSQL integration | Liquibase, constraints/indexes/partition behavior, JDBC batches, transaction rollback, lease claim/expiry, MVCC projection publication and query plans | Testcontainers PostgreSQL matching supported major version; never substitute H2 for SQL behavior |
| API contract | Analytics, Generator and Auth OpenAPI schema, auth, parameters, status/error shapes, examples and generated client compatibility | OpenAPI lint in CI; operation inventory test covers every `operationId`; controller tests exercise representative success and all shared error mappings |
| Golden end-to-end | Scenario → Generator run → raw batch → calculation → intervals/minute rollups → frontend read; incident/recalculation overlay | Fixed seed + fixed clock fixture, expected raw/interval/numerator-denominator outputs checked into test resources |
| Load/performance | Full demo stack on 4 vCPU/8 GB, realtime/read concurrency, burst recovery and 20M historical import | Record p50/p95/p99, accepted/dropped counts, lag/backlog, locks/connections, CPU/RAM/disk; compare to load/SLO spec |
| Recovery/resilience | Crash between raw commit and ack, worker staging and publish, lease expiry, retry of same batch/run/job, observability unavailable | No duplicate additive effect, no partial published range, recoverable durable state; service remains available within its stated degradation policy |

## Critical unit and property cases

- Comparison operators: inclusive/exclusive boundaries, exact tolerance edges, null/UNKNOWN, invalid quality, numeric/string/boolean types and IN membership semantics.
- State evaluator: priority, activation/release delay, hysteresis, stale and offline deadlines; tie at deadline uses the documented event-time boundary and emits at most one valid transition.
- Shift calendar: local day/night occurrence, cross-midnight `shiftDate`, DST spring gap and autumn overlap according to the single selected calendar policy; `shiftId` remains enterprise-defined.
- Metrics: zero denominators return the documented null, planned stop/offline treatment, production unit compatibility and weighted cross-machine ratios.
- Intervals: normalized output is sorted, gap/overlap-free where coverage is expected, duration sums equal covered duration, and rerun/replace yields the same projection.
- Scenario compilation: base behaviors plus phase `REPLACE|DISABLE` produce the same effective matrix saved in immutable run snapshot; same seed and inputs generate the same historical values.

## PostgreSQL concurrency checks

- Run ingestion and current/history readers while a recalculation stages outside the publish transaction. Assert readers do not wait on the long replay and see only the prior committed range until atomic publication.
- While a publication transaction executes, measure its duration and verify raw ingestion continues under the load SLO; publication must be range-scoped and short.
- Compete two workers for dirty work/deadlines and verify `FOR UPDATE SKIP LOCKED` gives one active lease per row; expired lease becomes recoverable.
- Verify rollback of a failed batch/incident/config command leaves no partial rows or durable hint that claims success.
- Verify locks are acquired in documented stable order and user-facing contention exits without partial mutation.

## Contract and acceptance coverage

- CI inventories all **77** Analytics (63), Generator (12), and Auth (2) `operationId`s; every operation has valid schema, applicable security requirement, documented success response and shared error model. Breaking generated-client changes fail review/CI.
- AC-1…AC-11 are executable acceptance tests, grouped by application boundary where practical. Each test records operationId(s) and source-spec section in its test name or traceability file.
- Do not duplicate every field schema rule as prose: OpenAPI validates transport shape, domain tests validate invariants, and workflow cases validate cross-resource behavior.

## Load and restore gates before demo release

- Execute the benchmark procedure and thresholds in `spec-mvp-load-slo/slo-and-benchmarks.md` without silently relaxing current-read protection.
- Backup job: verify one successful custom-format dump, checksum/size result, age alert, and restrictive permissions. Before release, restore the dump into an isolated database and run migration/read smoke checks; target manual restore RTO is four hours and RPO is one day.
- Execute failure injection for calculation worker restart and Generator retry; capture no partial projection, duplicate batch, or lost durable run state beyond the documented raw-overload drop policy.
- Test DNS/TLS proxy setup with both Certbot/valid wildcard certificate procedure and self-signed local/demo mode per security/deployment contract; secrets are supplied out of Git.

## Not required for MVP

- Exhaustive combinatorial cross-product testing across every signal type, rule operator, shift, state, and API error; use boundary partitions and risk-based coverage.
- Multi-node/HA failover, chaos across cloud zones, long-duration compliance backup retention, and soak beyond agreed benchmark windows.
