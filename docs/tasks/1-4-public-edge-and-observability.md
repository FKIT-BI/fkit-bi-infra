# Evidence: Story 1.4 — public edge and observability

## Implemented

- Nginx is the only public service on ports 80/443; Analytics, Generator, PostgreSQL, Prometheus and exporters have no host ports. Grafana is bound to loopback.
- Added `TLS_MODE=off|self-signed|public`, persistent self-signed cert generation, Certbot DNS-01 setup/renewal, and Yandex Cloud DNS auth/cleanup hooks that preserve other TXT values.
- Provisioned Prometheus scrape jobs, seven-day/one-GB retention, alert rules, Grafana datasource and six dashboards.
- Enabled Micrometer Prometheus endpoints and JSON console logs in both Java services. Trace IDs are validated, returned, and added to MDC. Nginx blocks public Prometheus paths.
- Updated operator and infra-delivery scripts to start the default monitoring stack and reject the effective Grafana placeholder password.
- Certbot setup/renew now use an explicit shell entrypoint; legacy lineage snapshots preserve resolved certificate/key files; self-signed cert reuse validates key, expiry, and both DNS names.
- Ingestion/generation dashboard explains that domain telemetry panels are pending follow-up instrumentation.

## Verification

- `./scripts/validate.sh` — passed: Compose/TLS-mode config and Certbot entrypoint, delivery stubs, HTTP/TLS Nginx routes (including public metrics 404), mocked DNS hook tests, TLS setup behavior, Prometheus config/rules/tests, shellcheck, actionlint, and a live monitoring-isolation smoke.
- Analytics `mvn -B verify` — passed, 31 tests.
- Generator `mvn -B verify` — passed, 20 tests.

## Remaining limitation

Analytics and Generator still do not implement the ingestion/calculation operations behind the domain-specific custom metrics; the dashboard marks those panels as pending. No external DNS API, live ACME issuance/renewal, or deployment was run.
