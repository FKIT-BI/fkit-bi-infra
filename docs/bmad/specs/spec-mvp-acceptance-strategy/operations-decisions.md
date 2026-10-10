# MVP operational decisions

## PostgreSQL backup and restore

- Produce one PostgreSQL custom-format logical dump per day during the lowest-activity window; do not run a full dump on the hot ingestion transaction or hold application locks for its duration.
- Keep seven most recent local restore points in a mounted backup directory with restrictive owner-only permissions. The location and database credentials come from deployment secrets/configuration, never Git.
- Treat **RPO ≤24 hours** and **manual restore RTO ≤4 hours** as demo-MVP targets. No point-in-time recovery, WAL archive service, automated failover, or HA replica is introduced.
- Bound backup CPU/I/O where the runtime permits; expose last-success timestamp, duration, size and failure/age status to logs/alerts. A missed daily backup is an operational warning.
- Before each demo release, restore the newest dump into an isolated database, verify database connectivity, schema release, Liquibase state, and a representative read path. Record timestamp and result.
- Local-only backups do not survive host loss. If host-loss recovery is required, deployment operator must copy encrypted backups off-host; that copy is outside application MVP automation.

## Raw partition lifecycle

- Raw telemetry retention is 90 days, measured against UTC partition upper bounds. Drop a partition only after its exclusive upper bound is at or before `now() - 90 days`; do not delete individual hot-path rows.
- Pre-create partitions through at least seven days ahead. Partition creation/drop runs as bounded maintenance outside ingestion transactions and emits outcome metrics/logs.
- Retain all minute/interval projections for the demo history according to existing analytics storage specs. Raw expiry does not silently delete projections.
- Maintenance must not drop a range while an active calculation/recalculation references it. Detect and defer safely; never block raw inserts waiting for replay.

## Structured logs and correlation

- Emit one JSON object per line to stdout with `timestamp`, `level`, `service`, `event`, `traceId`, and a concise message; add bounded domain fields such as `jobId`, `runId`, `machineId`, `batchId` where useful.
- At HTTP ingress, accept a valid bounded trace header or generate a UUID; return it as `X-Trace-Id` on success and error, and include it in the common error body. Do not permit arbitrary oversized or malformed trace values.
- Durable asynchronous jobs persist the initiating trace as `correlationId` and retain their own job/run IDs, so logs remain correlatable after the initiating request ends.
- Never log password, bearer/JWT, signing key, database credential, DNS/certificate secret, or raw telemetry body/value. Exception logs use safe error codes and trace context, not request dumps.
- High-cardinality IDs belong in structured logs, not Prometheus labels. Log transport remains stdout; Loki/Tempo and an external tracing backend are not MVP requirements.
