# Reviewer Gate: SQL normalization and data integrity

**Target:** `ARCHITECTURE-SPINE.md`  
**Lens:** normalization, referential integrity, duplicate facts, JSONB boundaries, `CHECK`/FK/index design, raw telemetry hot path and companion-spec consistency  
**Date:** 2026-10-09  
**Mode:** validation only; source artifacts were not changed

## Gate verdict

**CONDITIONAL PASS — the overall model is sound for the MVP, but it is not implementation-ready until four high-severity integrity/operability gaps are fixed in the contract.** The relational equipment core is appropriately normalized, the limited JSONB use is justified, and daily event-time partitioning with one signal/time index is proportionate to the accepted load. The principal risks are not classic normalization errors; they are undefined cross-service encodings, concurrency gaps in application-enforced invariants, loss of durable evidence after raw retention, and unbounded/hard-to-clean hot-path data.

Mechanical spine lint passed with zero findings.

## What is already correct

1. **Equipment ownership is normalized without losing unassigned-machine semantics.** Keeping `machine.enterprise_id` alongside nullable `line_id` is not accidental duplication: Enterprise is the machine's permanent owner, while Line is an optional one-time placement. The composite FK `(enterprise_id, line_id) -> production_line(enterprise_id, id)` prevents divergence. The same reasoning correctly applies to `telemetry_signal.machine_id + component_id` and `component.machine_id + parent_component_id`.
2. **The technical composite `UNIQUE(owner_id, id)` constraints are justified.** They add small write/storage overhead only to low-volume configuration tables and let PostgreSQL enforce same-owner composite FKs without triggers.
3. **JSONB is used at an acceptable boundary.** `Machine.parameters` and `Component.parameters` are bounded, owner-contained display values and are explicitly excluded from filters, rules, formulas and analytics. Normalizing them into EAV tables would add joins and mutation complexity without improving the current use case. The top-level array `CHECK` plus mandatory application validation is proportionate because these values are not calculation inputs.
4. **The raw model is intentionally, not accidentally, denormalized.** Batch metadata is stored once in `ingest_batch`; measurements use typed nullable columns instead of JSONB; `received_at` is derived through the batch header rather than repeated per row. Omitting per-measurement FK/unique constraints is a defensible hot-path trade-off under a single writer and an atomic batch transaction, provided the writer contract and privileges are tested.
5. **The primary raw access path is well matched to the workload.** UTC-day partitions allow cheap retention and prune by time; `(signal_id, observed_at)` supports the only sanctioned raw query shape. Adding value/quality indexes before measured plans would be premature.
6. **Read/write separation is coherent.** Append-only inserts, MVCC reads without raw row locks, separately published projections and DDL outside the write transaction are compatible with the 4 vCPU/8 GB MVP envelope.

## High-severity findings

### H1 — Numeric storage codes are not defined across the two independently built services

**Evidence:** `telemetry-storage.md:21,41-42` selects `SMALLINT` for `mode` and `source_quality` and `INTEGER` for flags, while `writer-protocol.md:44-53` names the values but assigns no numeric codes or bit positions. The spine only says that the row is typed (`AD-5`) and does not close this divergence point.

**Impact:** Generator can encode `REALTIME`, `GOOD` or `OUT_OF_RANGE` differently from Analytics. Data remains valid at the SQL type level but is silently interpreted incorrectly. This is exactly the kind of incompatibility an architecture spine must prevent.

**Required disposition:** **autofix before DDL.** Bind exact mappings, for example:

- `mode`: `1=REALTIME`, `2=HISTORICAL`;
- `source_quality`: `0=GOOD`, `1=UNCERTAIN`, `2=BAD`;
- flags: fixed powers of two (`1,2,4,8`) with stable meanings.

Add DB `CHECK` constraints for mode/quality and at minimum `validation_flags >= 0`; keep unknown future flag bits readable rather than rejecting them unless a versioning rule is introduced. Alternatively store short `VARCHAR` values, but both services must use one normative mapping.

### H2 — “Immutable after first raw” is neither retention-safe nor race-safe

**Evidence:** `schema-model.md:148` and `integrity-and-indexes.md:33` require a transaction-time existence check for raw/analytics data. Raw is deleted after 90 days (`telemetry-storage.md:70`), and raw ingestion deliberately has no FK or lock protocol with `equipment.telemetry_signal` (`ARCHITECTURE-SPINE.md:73-77`).

**Impact:**

- after raw retention, the fact that a signal has ever received data can disappear, allowing semantic fields to be changed and surviving projections/history to be reinterpreted;
- concurrently, configuration can check “no raw exists” while Generator validates an old snapshot and inserts the first raw batch, so both transactions can commit with different meanings for the same `signal_id`;
- the same class of issue affects Enterprise timezone locks if their only evidence is expiring raw data.

**Required disposition:** **discuss and bind a durable protocol before implementation.** Recommended minimal design:

- persist one non-expiring usage marker per signal, e.g. `telemetry.signal_usage(signal_id PK, first_observed_at)`, inserted once per distinct signal (`ON CONFLICT DO NOTHING`) and never removed with raw retention;
- define one shared per-signal serialization mechanism for the first-use/configuration race: both semantic update and first-use registration acquire the same advisory lock, or both lock the same signal row in a documented order;
- use an equivalent durable enterprise-level temporal-use marker, or derive it from retained non-expiring usage/projection/run facts with a precise query contract.

This marker is deliberate derived state, not harmful fact duplication: its purpose is to preserve an irreversible lifecycle fact beyond raw retention.

### H3 — Cross-row invariants are transactionally checked but not actually serialized

**Evidence:** `integrity-and-indexes.md:31` locks only the component being moved before a recursive cycle check. Shift overlap checking is delegated to the application (`integrity-and-indexes.md:26`) without an Enterprise-scoped lock. `AD-4` promises consistent ownership but the spine does not define an aggregate lock boundary.

**Impact:** Two concurrent requests can each validate against the pre-commit graph and jointly create a cycle (for example `A -> B` and `B -> A`). Two concurrent Shift creates/updates can each observe no overlap and commit overlapping schedules. One Analytics instance does not eliminate concurrent HTTP transactions.

**Required disposition:** **autofix in the architecture/spec before repositories are built.** Define stable aggregate serialization:

- every Component hierarchy mutation locks the owning Machine row (or the same machine-scoped advisory key) before the recursive check and update;
- every Shift schedule mutation locks the owning Enterprise row (or enterprise-scoped advisory key) before loading all applicable shifts and checking overlap;
- all operations for the same aggregate acquire locks in one documented order.

This remains much simpler and safer than recursive/temporal triggers and has negligible cost for configuration traffic.

### H4 — Unbounded hot-path text and undefined `ingest_batch` retirement threaten availability

**Evidence:** `telemetry-storage.md:17-18,40` uses unbounded `TEXT` for both idempotency-key columns and `value_text`. The former participate in a unique B-tree; the latter sits in the highest-volume table. `load-profile.md:32` gives both `raw_measurement` and `ingest_batch` a 90-day lifetime, but `telemetry-storage.md:70` defines only partition retirement for raw and gives no cleanup key/index/algorithm for the non-partitioned batch table.

**Impact:** Oversized producer keys can bloat or exceed PostgreSQL B-tree entry limits; oversized string measurements can force TOAST and defeat the disk/latency budget. At a 1–2 second time flush, `ingest_batch` can accumulate millions of rows in 90 days even at modest measurement rates. Without an indexed bounded cleanup, its unique index grows and row deletes create avoidable vacuum/bloat work.

**Required disposition:** **autofix before DDL.** Recommended contract:

- bound `producer_id` and `producer_batch_id` (for example `VARCHAR(128)` plus API validation);
- bound `value_text` by the supported signal contract (the earlier design's `VARCHAR(500)` is reasonable for state/category values); consider byte-length validation if UTF-8 storage is the actual resource concern;
- use `TIMESTAMPTZ(3)` explicitly for all batch/raw timestamps to match the global convention;
- define header retention using an indexed key such as `max_observed_at`, delete in bounded chunks after all relevant raw partitions are gone, and monitor dead tuples/vacuum;
- define the idempotency horizon after header deletion and reject historical runs outside the active 90-day raw window unless a separate temporary-backfill lifecycle is deliberately added.

## Medium-severity findings

### M1 — Same idempotency key with different content is silently accepted

`writer-protocol.md:26-31` treats every conflict as the already accepted package, but stores no content fingerprint. A producer bug that reuses `producerBatchId` for a changed payload silently loses the second payload while reporting success.

**Disposition:** **discuss.** A `payload_hash` on a canonical batch representation is low-cost at the accepted rates and converts silent loss into an explicit idempotency-key conflict. If rejected for MVP, state the producer uniqueness assumption and add a contract test proving batch IDs are never reused inside a run.

### M2 — Raw-to-batch integrity is relaxed more broadly than the performance argument requires

The absence of an FK to `TelemetrySignal` is justified by hot-path independence. The absence of both FK and uniqueness for `(ingest_batch_id, ordinal)` also means PostgreSQL cannot reject orphan rows, duplicate ordinals or count mismatches. Atomic application writes prevent normal retry duplication, but not repository bugs or privileged manual inserts.

**Disposition:** **defer only with explicit safeguards.** Retaining the current no-FK/no-unique design is acceptable for the MVP if:

- Generator has only the exact INSERT privileges required and no UPDATE/DELETE on raw;
- integration tests assert header count/min/max, sequential unique ordinals, rollback on every induced failure and no measurements on duplicate-batch retry;
- an offline consistency diagnostic can detect orphan batch IDs and `measurement_count` mismatches.

Do not describe the omission as a normalization gain; it is a measured integrity/performance trade-off to revisit after benchmark results.

### M3 — The initial Shift index is optimized for administrative lists, not historical event-time resolution

`shift (enterprise_id, status, valid_from, valid_to)` places `status` before validity dates, while the agreed event-time algorithm explicitly ignores current status for historical assignment. PostgreSQL 16 cannot efficiently use the later validity columns when status is not constrained.

**Disposition:** **defer until representative plans**, because the MVP has only a handful of shifts per enterprise. Keep the current list index if useful, but benchmark a separate `(enterprise_id, valid_from, valid_to)` index before shift volume grows. This is not an implementation blocker.

## Low-severity consistency findings

1. `SPEC-raw-telemetry-ingestion.md` lists “normative raw retention duration” as a non-goal while the same spec and its companions now normatively fix 90 days. Remove that stale non-goal during the next spec refresh.
2. The raw companion uses bare `TIMESTAMPTZ` while the spine and equipment conventions require `TIMESTAMPTZ(3)`. The DDL should not leave precision to inference.
3. The stack versions are internally consistent with the brownfield project: Spring Boot `3.5.0` is the current parent in `fkit-bi-analytics/pom.xml`, and its locally resolved dependency BOM contains Liquibase `4.31.1` and PostgreSQL JDBC `42.7.5`. The current code still contains Flyway by design; the Liquibase companion explicitly treats replacement as implementation work, so this is not an architecture contradiction.

## Good-spine checklist assessment

| Criterion | Result | Notes |
| --- | --- | --- |
| Fixes real divergence points | **Partial** | Ownership, schemas and hot/read paths are fixed; numeric encodings and aggregate lock scopes are not. |
| Every AD is enforceable | **Partial** | AD-1/2/3/7/10/11 are directly enforceable. AD-4 depends on an incomplete concurrency protocol; AD-5/6 depend heavily on application tests. |
| Deferred items are safe to defer | **Mostly** | Extra raw indexes and horizontal scaling are safely deferred. Header retirement and historical admission window are missing rather than deferred. |
| Technology versions fit brownfield | **Pass** | Pinned values match the current Maven parent/BOM and PostgreSQL target. |
| Ratifies rather than contradicts codebase | **Pass with planned migration** | Flyway-to-Liquibase divergence is explicitly acknowledged as future implementation. |
| Covers source-spec capabilities | **Partial** | Main capabilities map correctly; immutable-after-first-use and batch/header lifecycle are not made durable. |
| Operational envelope covered | **Pass** | Resource envelope, connection budgets, retention, DDL isolation and benchmark are present. |
| Normalization/duplication justified | **Pass** | Configuration is normalized; owner duplication is constrained; raw denormalization is explicit and bounded in purpose. |
| JSONB boundary safe | **Pass** | Only display-only embedded parameters use JSONB; calculations and filtering cannot depend on them. |

## Recommended gate action

Before Liquibase DDL is authored, amend the spine/companions for **H1–H4**. Keep the fundamental design — one PostgreSQL, normalized equipment configuration, typed append-only raw rows, daily partitions and projection-only frontend reads. No database split, Kafka or generic EAV model is warranted by this review.

After those amendments, the design should be re-linted and validated with PostgreSQL integration tests plus the already specified 20-million-row benchmark. M1 can be accepted or explicitly deferred by the user; M2 must at least receive the stated safeguards.
