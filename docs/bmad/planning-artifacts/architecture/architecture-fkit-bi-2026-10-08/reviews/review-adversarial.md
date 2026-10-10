# Adversarial review — FKIT BI data path

**Artifact:** `ARCHITECTURE-SPINE.md`  
**Lens:** independently implemented Analytics, Generator and partition maintenance  
**Date:** 2026-10-09  
**Verdict:** **NEEDS CHANGES — 1 critical, 4 high findings**

## Executive assessment

The relational shape is appropriate for the MVP. The equipment/configuration core is normalized along ownership boundaries, reusable semantic and unit values are dictionaries, and JSONB is confined to validated display-only parameters. The telemetry split between a batch header and typed measurement rows is also a reasonable deliberate hot-path denormalization: it avoids repeating producer metadata while retaining native value types. Daily event-time partitions and a single `(signal_id, observed_at)` index are proportionate to the stated workload. PostgreSQL does not need to be replaced by a TSDB or message broker for this MVP.

The spine does not yet make the operational seams executable. A team can build Analytics, Generator and maintenance in mutually incompatible ways while formally complying with the current AD wording. The largest problem is that partition DDL is required but prohibited to all runtime roles. The remaining gaps concern content-blind idempotency, a race between historical/dirty processing and retention, unenforced resource isolation, and migration/startup compatibility.

## Findings summary

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| AR-1 | Critical | Partition maintenance has no authorized executor or complete lock protocol | Fix before SQL/Liquibase implementation |
| AR-2 | High | A batch identity is not bound to its content | Fix in ingestion schema and writer contract |
| AR-3 | High | Historical acceptance, durable dirty handoff and retention are not one coherent protocol | Discuss one boundary, then fix before workers |
| AR-4 | High | Connection and disk ceilings do not enforce workload isolation on 4 CPU / 8 GB / 100 GB | Fix configuration invariants and admission rules |
| AR-5 | High | Migration success is not a deployment/schema-compatibility protocol | Fix startup topology before Compose implementation |

## Detailed findings

### AR-1 — Critical — Partition maintenance has no authorized executor or complete lock protocol

**Evidence**

- AD-10 requires Analytics maintenance to create and remove partitions outside the hot transaction and to use bounded lock wait (`ARCHITECTURE-SPINE.md:103-107`).
- AD-11 says runtime credentials do not apply migrations and have minimal grants (`ARCHITECTURE-SPINE.md:109-113`).
- The only DDL-capable role named by the design is `fkit_bi_owner`; there is no narrow maintenance capability, function, role or one-shot job.

**Adversarial compliant implementations**

1. Team A mounts `fkit_bi_owner` credentials into the long-running Analytics process so its scheduler can run DDL. Partitioning works, but compromise of the application gives ownership of every schema and invalidates the intended least-privilege boundary.
2. Team B gives Analytics only the declared runtime grants. It cannot create the next daily partition; because there is no default partition, the first event beyond the existing horizon fails hard.
3. Team C creates partitions only through Liquibase. Realtime works for the fixed horizon, but an arbitrary permitted historical interval cannot be prepared without a new deployment.
4. Two maintenance invocations independently test partition existence, then one creates while the other detaches or creates the same relation. Both are compatible with “outside the hot path”; the result is lock contention or a failed maintenance run.

Partition attach/detach changes the parent partition topology and requires locks on the parent. `bounded lock wait` on retention alone does not prevent a create or detach operation from briefly blocking writers, nor does it serialize create versus retention.

**Impact**

- inevitable insert failures when the partition horizon is exhausted;
- risk of broad owner credentials in the application container;
- avoidable writer stalls and partition-name races;
- a partition may become visible before its required index if creation and indexing are not atomic.

**Required resolution**

Adopt one explicit MVP protocol:

1. Liquibase remains the only general DDL mechanism and runs with `fkit_bi_owner`.
2. Liquibase installs narrowly scoped `SECURITY DEFINER` functions for `ensure_raw_partition(day)` and `retire_raw_partition(day)`. They must have a fixed safe `search_path`, validate a UTC date against allowed bounds, derive/quote the relation name internally, and accept no SQL or relation name from the caller.
3. Grant only `EXECUTE` on those functions to `fkit_bi_analytics`; do not mount owner credentials into the long-running runtime.
4. Both functions use the same transaction-scoped advisory-lock namespace for partition topology. Creation, attachment and local-index creation are committed atomically. Retention obtains the same topology lock, uses a small `lock_timeout` and `statement_timeout`, detaches first, and drops the already detached table separately. A lock miss is a retryable maintenance result, never an ingestion wait policy.
5. Define one scheduler owner and idempotent reconciliation on startup. Even with a single Analytics instance, duplicate scheduler execution must be harmless.
6. Generator receives no DDL capability. Its readiness check verifies that every day required by a historical run is already attached and indexed before the run starts.

**Verification**

- Hold an open transaction that reads or inserts through the partitioned parent; run retention and prove it exits within the configured lock timeout without delaying an unrelated current-day insert beyond the ingestion timeout.
- Start two `ensure` calls for the same day and one retention call; exactly one indexed attached partition must remain, with no invalid/pending relation.
- Exhaust the future horizon in a test and verify the readiness/alert fires before any producer reaches the missing day.
- Inspect container secrets and PostgreSQL grants: the Analytics runtime must not possess `fkit_bi_owner` credentials or generic `CREATE/DROP/ALTER` privileges.

### AR-2 — High — A batch identity is not bound to its content

**Evidence**

AD-6 makes `(producer_id, producer_batch_id)` unique and says a duplicate returns the accepted result without reinsertion (`ARCHITECTURE-SPINE.md:79-83`). The writer protocol returns success on any conflict, but the header has no content digest. The current rule therefore proves “one write per key”, not “a retry of the same write”.

**Adversarial compliant implementations**

- After a crash, one Generator reconstructs a checkpoint batch with a different ordering, quality flag or value but reuses its deterministic ID. The writer sees the prior key and silently reports success for content it never stored.
- Two accidental concurrent producers share `producer_id` and `producer_batch_id`. The winner commits one payload; the loser receives the winner’s accepted result even though it submitted a different payload.

PostgreSQL's unique index can safely serialize the key race, but it cannot establish content equivalence.

**Impact**

Silent measurement loss/corruption is reported as successful idempotent recovery. This is harder to detect than the explicitly accepted observable telemetry loss.

**Required resolution**

- Add `payload_hash BYTEA NOT NULL` to `telemetry.ingest_batch`.
- Define a single canonical SHA-256 input: producer sequence, optional run ID, mode, and all measurements in ordinal order including signal ID, millisecond timestamp, value type/value, source quality and source flags. Exclude server-assigned fields.
- Use `INSERT ... ON CONFLICT DO NOTHING RETURNING ...`. If no row is returned, read the now-committed header under `READ COMMITTED` and compare the hash. Equal means idempotent success; unequal means a stable `BATCH_ID_REUSED_WITH_DIFFERENT_PAYLOAD` error. The unique-index wait resolves the concurrent race; if the competitor rolls back, the insertion can become the winner.
- A corrected batch always receives a new batch ID, as already required.

**Verification**

- Submit identical packets concurrently: one physical batch and one set of measurements exist, and both callers receive the same accepted identity.
- Submit different payloads under the same key concurrently and sequentially: one is accepted and the other receives the conflict error, never success.
- Kill the writer after server commit but before client acknowledgement; retry produces no duplicate rows.

### AR-3 — High — Historical acceptance, durable dirty handoff and retention are not one coherent protocol

**Evidence**

- AD-7 fixes a 90-day event-time retention but does not define a writable historical boundary (`ARCHITECTURE-SPINE.md:85-89`).
- AD-10 says partitions are prepared and later retired, but does not bind retention to unprocessed ingestion or active/retryable dirty work (`ARCHITECTURE-SPINE.md:103-107`).
- The companion says historical ingestion creates dirty windows “after commit”. No durable atomic handoff between Generator's raw commit and Analytics' dirty queue is fixed by the spine.
- The companion retention text contains the intended “no intersecting dirty window and projections published” rule, but omitting it from the architecture invariant permits independently built maintenance to ignore it.

**Adversarial compliant implementations**

1. Generator accepts data from one year ago after maintenance prepares the partition. The next 90-day retention pass immediately regards that partition as expired.
2. Generator commits raw, crashes before notifying Analytics, and resumes from its checkpoint. The raw remains, but no projection is dirtied.
3. Retention checks that no dirty row is currently `RUNNING`; a worker claims or creates work immediately after the check, then the partition is detached while the worker reads it.
4. Retention drops the oldest UTC day exactly 90×24 hours ago although the partition contains a still-retained tail because the retention boundary falls inside the day.

**Impact**

- accepted historical raw can disappear before calculation;
- analytics can permanently omit committed raw;
- a recalculation can fail halfway or publish incomplete output;
- retention semantics differ by application clock and UTC-day rounding.

**Required resolution**

For the MVP, choose and bind the simpler policy:

1. Historical `observed_at` must fall inside the active 90-day raw window. Define the exact UTC-day boundary from PostgreSQL time; only fully expired daily partitions are eligible for retirement. Arbitrarily older generation requires a future archive/import design, not temporary old partitions.
2. Commit a durable recalculation hint in the same transaction as header and raw rows. A practical shared-DB contract is one append-only `telemetry.recalculation_hint` row per affected machine/range in the batch; Analytics idempotently coalesces those hints into its dirty queue. A post-commit in-memory callback is not sufficient.
3. Retention eligibility requires all of: fully older than the boundary, no unconsumed hint, no queued/running/retryable dirty or full-recalculation job intersecting the day, and all dependent projections published through the day end.
4. Make check-and-detach race-free. Workers reading a day and retention must share a per-day lease/advisory-lock convention; retention uses a nonblocking/exclusive attempt and retries later on contention.
5. A failed dirty job remains retention-blocking until resolved or explicitly abandoned by an operator-visible action. Merely changing it to `FAILED` must not make its source raw deletable.

If the business later needs history older than 90 days, retention or a separate archive must change first; the writer must not improvise old partitions.

**Verification**

- Crash between raw commit and Analytics consumption; after restart, the durable hint is consumed and projections catch up.
- Race retention against a worker holding a per-day read lease; retention must defer without interrupting or partially publishing the worker.
- Attempt historical generation just before and just after the exact retention boundary and assert deterministic acceptance/rejection.
- Leave a dirty job failed for an old day; retention must report why it skipped that partition.

### AR-4 — High — Connection and disk ceilings do not enforce workload isolation on 4 CPU / 8 GB / 100 GB

**Evidence**

AD-9 limits Analytics to 14–16 connections and Generator to 2–3, but does not reserve connections or concurrency for the read path (`ARCHITECTURE-SPINE.md:97-101`). The Availability convention states a reserve exists but gives independently built modules no enforceable boundary (`ARCHITECTURE-SPINE.md:123`). The spine also omits the 100 GB storage envelope and disk-pressure behavior even though it binds the limited resource profile.

**Adversarial compliant implementations**

- Analytics uses one 16-connection pool. Calculation jobs borrow all 16 while queries wait in the pool. The total limit is obeyed, but frontend reads are blocked.
- Generator uses its three connections for historical writes, queues realtime behind them, and remains within AD-9.
- Historical runs are repeated with new valid batch IDs. Each is intentionally new data; the batch key and 90-day retention do not cap volume. Disk fills even though all components meet the rate limits.
- `200 measurements/s sustained` is interpreted as a 90-day supported profile. That is about 1.56 billion rows, not the 30-minute benchmark defined in the source load profile.

At the nominal 30 measurements/s, 90 days is about **233 million raw rows** before headers, projections, WAL, temporary space and observability. A 100 GB SSD is plausible but not self-proving; it has materially less safety margin than a row-count-only reading suggests. The 200/s and 1000/s figures are short benchmark envelopes, not retention capacity.

**Impact**

- connection-pool starvation violates the central no-read-blocking goal without any PostgreSQL lock;
- disk exhaustion can stop PostgreSQL and take both reads and writes down;
- JVM native memory, PostgreSQL per-query memory and page cache can exceed the 8 GB envelope even when configured heaps fit.

**Required resolution**

- Bind a real bulkhead, not only a total: reserve a minimum query capacity and limit concurrent calculation, recalculation, maintenance and historical transactions with separate pools or semaphores. Neither calculation nor ingestion may borrow the final query reserve. Define bounded acquisition and statement timeouts per workload class.
- State explicitly that 200/s means at least 30 minutes and 1000/s means 60 seconds; neither is a 90-day supported rate.
- Before a historical run, estimate its measurement count/bytes and verify a storage budget. At less than 20% free space, pause/reject new historical work; at a critical floor, preserve PostgreSQL/read availability by stopping historical and other nonessential writers rather than hoping retention can free blocked dirty partitions.
- Reserve disk for WAL, temporary files, maintenance and observability. Do not count the entire 100 GB as raw capacity.
- Keep 100 GB as a **benchmark candidate**, not a proven guarantee. Promote it to an accepted minimum only after measuring heap+index bytes/row, projection growth and peak WAL/temp usage with the nominal 90-day equivalent and the 20-million-row import.

**Verification**

- Occupy every worker permit and run historical input; five read clients must still acquire connections and meet the protective SLO.
- Repeatedly request historical runs until the preflight crosses the disk threshold; the next run must be rejected/paused without affecting current reads.
- Run the required benchmark with container memory limits and record OOM, swap, pool wait, PostgreSQL memory, filesystem free space and WAL peak, not only API latency.

### AR-5 — High — Migration success is not a deployment/schema-compatibility protocol

**Evidence**

AD-2 says Analytics alone runs Liquibase and migration success precedes Generator readiness (`ARCHITECTURE-SPINE.md:55-59`). AD-11 separates owner and runtime credentials (`ARCHITECTURE-SPINE.md:109-113`). The spine does not say whether Liquibase is an init job or part of the long-running Analytics process, how Generator proves compatibility, or what happens to a running Generator during a schema-changing redeploy.

**Adversarial compliant implementations**

- Analytics starts with both owner and runtime secrets, runs Liquibase, then retains the owner secret for its lifetime.
- Compose starts Generator after an Analytics HTTP health check that says only “process up”; Generator's required telemetry table or column is not verified.
- An old Generator remains running while a new Analytics release performs a destructive migration. Liquibase itself succeeds, but Generator executes SQL for the previous schema.
- Analytics becomes ready although the future partition horizon or required seed dictionaries are incomplete; Generator begins a run and fails only on first write.

**Impact**

Startup can be green while the shared DB contract is incompatible. Migration DDL can also compete with live writes, and owner credentials can leak into runtime.

**Required resolution**

Use a deliberately simple coordinated MVP deployment:

1. Stop writers for schema-changing deployment.
2. Run a one-shot migration command from the Analytics artifact with `fkit_bi_owner`; the owner secret is mounted only into that command.
3. Start Analytics with only `fkit_bi_analytics`. Its readiness checks the expected schema-release marker, mandatory seed/catalog rows and minimum future partition horizon.
4. Start Generator with only `fkit_bi_generator` after Analytics readiness, and make Generator independently fail readiness when the schema-release marker is outside its declared compatible range.
5. Grant Generator only the concrete append rights it needs: `INSERT`/idempotency read on batch headers, `INSERT` on raw/hint, required sequence usage, selected equipment reads and DML in `generator`; deny telemetry `UPDATE/DELETE` and all DDL.
6. Defer rolling/zero-downtime database upgrades explicitly. When needed, require expand/contract migrations; do not infer rolling safety from Liquibase success.

**Verification**

- Start Generator against an empty, older and newer-incompatible schema; readiness must remain false and no run may start.
- Verify the owner credential is absent from long-running Analytics and Generator containers.
- Interrupt Liquibase halfway through a test changeset; applications remain unready until a subsequent migration run completes consistently.
- Start the complete Compose stack from an empty volume and from the previous release's database, then prove deterministic ordering and readiness.

## Minimal architecture amendments

The findings do not require a redesign. The smallest convergent change is to amend/add invariants with these rules:

1. **Partition capability:** Analytics runtime calls only audited definer functions; a shared advisory lock, atomic indexed creation, bounded detach and retry govern all topology changes.
2. **Content-bound idempotency:** the batch key plus canonical payload hash identify one immutable accepted payload; a mismatched duplicate is an error.
3. **Durable projection handoff:** raw and per-machine dirty hints commit together; retention cannot detach a day while a hint/job/worker lease or unpublished projection intersects it.
4. **Writable retention window:** MVP historical generation is restricted to the active raw window with a database-time UTC-day boundary.
5. **Resource bulkheads:** query capacity and disk headroom are reserved; historical work is rejected/throttled before it can exhaust either.
6. **Migration lifecycle:** owner-only one-shot migration precedes runtime startup; runtime readiness checks an explicit compatible schema release and partition horizon.

## Final conclusion

The chosen normalization and PostgreSQL-first design are suitable and should be retained. On the nominal profile, Java 21 plus PostgreSQL 16 can plausibly operate on 4 vCPU / 8 GB, and 100 GB may be sufficient, but only as a benchmarked lower bound with historical admission control. Implementing the current spine literally without the five fixes above can still produce write outages, silent idempotency loss, incomplete analytics, query starvation or a startup that is healthy against an incompatible schema.
