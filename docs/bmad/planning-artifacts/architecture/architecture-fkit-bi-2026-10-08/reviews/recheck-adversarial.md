# Adversarial recheck — FKIT BI data path

**Artifact:** `ARCHITECTURE-SPINE.md`  
**Lens:** Analytics, Generator and maintenance divergence  
**Date:** 2026-10-09  
**Verdict:** **PASS WITH CLARIFICATIONS — no redesign required; 2 high and 1 medium finding**

The amended spine now converges the three implementations on physical telemetry codes, content-bound batch identity, durable hints, partition ownership, topology locking, grants and a bounded shared pool. In particular, AD-9 is sufficient for the MVP pool model: exact semaphore counts may remain runtime configuration validated by benchmark, because the invariant already forbids background work from consuming the query reserve. AD-10 also gives partition create/detach one topology-lock namespace and excludes DDL from ingestion.

## Findings

### RR-1 — High — Retention eligibility is stated, but check-and-detach is not race-free

AD-7 forbids retirement while hints, jobs/leases or unpublished projections intersect a partition, but it does not bind workers and retention to one atomic exclusion protocol. A compliant worker can create/claim a lease immediately after maintenance checks eligibility and before AD-10 detaches the partition. The topology advisory lock serializes maintenance DDL with other maintenance DDL; it does not serialize DDL with calculation lease acquisition.

**Required clarification:** define one per-UTC-day retention barrier. Before claiming/creating intersecting work, workers obtain a shared/read lease; retention obtains the exclusive/nonblocking form, rechecks all eligibility predicates while holding it, and then detaches. Failure to acquire it is a retry, never a wait on the hot path. The exact SQL representation belongs in the next analytics projection/job specification.

### RR-2 — High — “Canonical SHA-256” still lacks a byte-level canonical form

AD-6 fixes the fields and conflict outcome, while `writer-protocol.md` names a binary representation. It does not define field framing, byte order, null encoding, UUID/timestamp encoding, floating-point encoding, string charset or whether `-0.0` and NaN have normalized forms. Generator and another producer can therefore hash the same logical batch differently while both claim to use canonical SHA-256.

**Required clarification:** make one component authoritative for hash construction and publish the exact canonical codec with golden test vectors. For the simplest MVP, keep hash creation inside the shared Java telemetry-writer library used by every producer; persist and compare only its 32-byte output. Reject NaN/infinity before hashing as already required.

### RR-3 — Medium — Startup ordering does not define upgrade compatibility

AD-2 guarantees that Generator starts after Analytics readiness, but readiness proves migration success only for the current Analytics process. It does not prevent an older Generator binary from starting after a newer incompatible schema, nor state what happens to an already-running Generator during migration. Embedded Liquibase also leaves owner credentials available to the Analytics process for its lifetime even though the runtime datasource is restricted.

**Required clarification for the simplified MVP:** declare coordinated stop → Analytics migration/start/readiness → Generator start, with no rolling mixed-version deployment. Add a schema-release marker checked by both services, or explicitly require the two artifacts to share one release identifier. Moving Liquibase to a one-shot container may remain deferred; it is not required for MVP correctness under coordinated startup.

## Conclusion

The architecture is sufficiently complete to proceed to the next analytics block. RR-1 must be resolved in the projection/job/retention design, RR-2 in the writer contract before implementation, and RR-3 in deployment acceptance criteria. None requires changing the normalized equipment model, raw table shape, single-database decision or shared-pool MVP approach.
