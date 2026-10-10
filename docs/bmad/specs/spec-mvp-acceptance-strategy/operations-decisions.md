# MVP operational decisions

## PostgreSQL backup and restore

- Produce one PostgreSQL custom-format logical dump per day during the lowest-activity window; do not run a full dump on the hot ingestion transaction or hold application locks for its duration.
- Keep the **three most recent daily full backups** in a mounted backup directory with restrictive owner-only permissions. Each file is a compressed PostgreSQL custom-format logical dump of the whole application database, including schemas, tables/index definitions and data for equipment/configuration, telemetry raw rows still within retention, state/metric/loss projections, incidents, Generator scenarios/runs and Liquibase metadata.
- A database dump does not contain PostgreSQL cluster roles/users, host/Compose configuration, `.env` or other secrets, TLS private keys/certificates, container images, or Prometheus/Grafana volumes. The single test-contour PostgreSQL account is recreated from deployment configuration before restore.
- Treat **RPO ≤24 hours** and **manual restore RTO ≤4 hours** as demo-MVP targets. No point-in-time recovery, WAL archive service, automated failover, or HA replica is introduced.
- Bound backup CPU/I/O where the runtime permits; expose last-success timestamp, duration, size and failure/age status to logs/alerts. A missed daily backup is an operational warning.
- Before each demo release, restore the newest dump into an isolated database, verify database connectivity, schema release, Liquibase state, and a representative read path. Record timestamp and result.
- Local-only backups do not survive host loss. If host-loss recovery is required, deployment operator must copy encrypted backups off-host; that copy is outside application MVP automation.

## Raw partition lifecycle

- Raw telemetry retention is 90 days, measured against UTC partition upper bounds. Drop a partition only after its exclusive upper bound is at or before `now() - 90 days`; do not delete individual hot-path rows.
- Pre-create partitions through at least seven days ahead. Partition creation/drop runs as bounded maintenance outside ingestion transactions and emits outcome metrics/logs.
- Retain all minute/interval projections for the demo history according to existing analytics storage specs. Raw expiry does not silently delete projections.
- Raw insert takes a shared try-lock for its UTC day and commits the measurement plus durable hint in the same transaction. If unavailable, it returns a retryable result without waiting; the caller applies bounded retry, then the already-approved observable telemetry-loss policy. A calculation worker retains a shared lock for the duration of raw reads and projection publication; if unavailable, it leaves the durable job queued. Retention takes an exclusive try-lock, then rechecks durable hints/jobs/leases and incomplete projection publication; on conflict it skips that day and retries later. Partition DDL also has a short `lock_timeout` and is cancelled/retried on conflict. Frontend read API uses projections and never participates in this lock protocol.

## Structured logs and correlation

- Emit one JSON object per line to stdout with `timestamp`, `level`, `service`, `event`, `traceId`, and a concise message; add bounded domain fields such as `jobId`, `runId`, `machineId`, `batchId` where useful.
- At HTTP ingress, accept a valid bounded trace header or generate a UUID; return it as `X-Trace-Id` on success and error, and include it in the common error body. Do not permit arbitrary oversized or malformed trace values.
- Durable asynchronous jobs persist the initiating trace as `correlationId` and retain their own job/run IDs, so logs remain correlatable after the initiating request ends.
- Never log password, bearer/JWT, signing key, database credential, DNS/certificate secret, or raw telemetry body/value. Exception logs use safe error codes and trace context, not request dumps.
- High-cardinality IDs belong in structured logs, not Prometheus labels. Log transport remains stdout; Loki/Tempo and an external tracing backend are not MVP requirements.

## Public entrypoints and automatic TLS

- MVP uses one application host, `bi.kitexp.ru`; Analytics and Generator use path-based routes, so no `api.bi.kitexp.ru` or `generator.bi.kitexp.ru` A records are required. The only application DNS A record is `bi.kitexp.ru -> 45.132.176.28`. A wildcard A record is unnecessary. Do not publish an AAAA record unless the server has working public IPv6. DNS records map names to an IP, not a port.
- Public domain mode uses Certbot DNS-01 to issue one certificate containing both `bi.kitexp.ru` and `*.bi.kitexp.ru`, renews automatically, validates renewal and reloads Nginx. The IP endpoint `http://45.132.176.28` remains available over HTTP; HTTPS-by-IP is not required for the current development phase.
- For automatic DNS updates, use Certbot auth/cleanup hooks against the Yandex Cloud DNS API unless a maintained compatible plugin is verified at implementation time. Do not depend on the old `certbot-dns-yandexcloud` package without a compatibility check. For the wildcard certificate the hook creates/removes the temporary TXT challenge `_acme-challenge.bi.kitexp.ru`; no wildcard A record is required. It fails visibly if credentials, zone identifiers or API access are missing; it never silently changes public mode to self-signed.
- Operator creates a service account and grants `dns.editor` on the target DNS zone, then installs its credential as a host/deployment secret. Do not transmit or commit private key material. Required non-secret inputs are DNS folder/zone IDs and the current host public IP.
- Self-signed mode is explicit for test/demo; create the certificate automatically when the persistent certificate is absent and clearly report that browser/client trust is not automatic. Public mode remains the default for the public domain.
