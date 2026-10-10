# Recheck: normalization and integrity

**Target:** `ARCHITECTURE-SPINE.md` and the bound SQL/raw companions  
**Date:** 2026-10-09  
**Verdict:** **CONDITIONAL PASS.** The relational model remains normalized and proportionate for the MVP. H1 and H3 are closed; H4 is materially closed; H2 has the right durable state but its selected row-lock implementation conflicts with the declared database privileges. This is a local protocol correction, not an architecture redesign, and does not block moving on to analytical projections if it is recorded for the telemetry DDL/adapter implementation.

## H1–H4 disposition

- **H1 — closed.** `AD-12`, `telemetry-storage.md` and `writer-protocol.md` now bind identical numeric values for mode, quality and flag bits. Quality is no longer duplicated in flags.
- **H2 — partially closed.** Non-expiring `telemetry.signal_usage`, semantic recheck and a shared serialization protocol close retention and write-skew conceptually. The concrete `FOR SHARE` writer operation still needs a privilege-compatible implementation (finding 1).
- **H3 — closed.** Component mutations lock the owning Machine; Shift schedule mutations lock the owning Enterprise before cross-row validation.
- **H4 — materially closed.** Producer keys and string values are bounded, timestamps use `TIMESTAMPTZ(3)`, Historical is restricted to the active window, and batch-header cleanup is bounded and observable. The cleanup key/index should be named in the DDL contract (finding 3).

## Findings

### 1. High — first-use row lock conflicts with Generator's read-only equipment access

`writer-protocol.md` requires Generator to lock `equipment.telemetry_signal` rows with `SELECT ... FOR SHARE`, while `AD-3`/`AD-11` limit Generator to reading equipment and appending telemetry. PostgreSQL row-locking clauses require `UPDATE` privilege on the locked table, so the protocol cannot run under the intended minimal grants without giving Generator mutation authority over equipment.

**Minimal correction:** use one signal-scoped transaction advisory lock in both the writer and semantic-update command, followed by the same semantic recheck and `signal_usage` insert/check. This preserves H2 without granting Generator `UPDATE` on equipment. A narrowly scoped owner-defined function is an alternative, but is more machinery for the MVP.

### 2. Medium — durable Enterprise timezone lock is not bound explicitly

The equipment spec still says timezone becomes immutable after temporal operational data exists, but only Signal first-use persistence is specified. A minimal rule is enough: timezone update locks Enterprise and rejects when `telemetry.signal_usage` exists for any Signal reached through Machine of that Enterprise (and when Enterprise-scoped Shift/analytics facts already exist). This can reuse the existing durable marker; no new table is required.

### 3. Low — header cleanup predicate remains unnamed

`telemetry-storage.md` now requires an indexed bounded cleanup, but does not bind the predicate/index. To avoid incompatible DDL choices, use `ingest_batch(max_observed_at, id)` and delete bounded batches only when `max_observed_at` is older than the retained UTC boundary and the corresponding raw days are gone. This finishes H4 without partitioning `ingest_batch`.

## Compatibility conclusion

No new normalization conflict was introduced. Composite ownership FKs, bounded display-only JSONB, append-only typed raw rows, daily UTC partitions and projection-only frontend reads remain mutually consistent. The move to embedded Liquibase startup is also internally consistent between the spine and Liquibase companion; it is an accepted MVP simplification rather than a data-model issue.
