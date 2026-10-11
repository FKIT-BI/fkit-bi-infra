# FKIT BI infrastructure

Infrastructure repository for PostgreSQL, analytics, generator, web and nginx. Analytics owns the shared database migrations.

Copy `.env.example` to `.env` only on the Dev host. Run `./scripts/validate.sh` to validate Compose and scripts. Read `docs/architecture/`, `docs/development.md`, `docs/dev-deployment.md` and `docs/bmad/project-context.md` before changing shared contracts.

Generate `FKIT_JWT_SECRET` from at least 32 cryptographically random bytes, base64-encode it, and supply it to both services through the deployment environment. After Analytics is running, set `FKIT_BOOTSTRAP_USERNAME`, `FKIT_BOOTSTRAP_DISPLAY_NAME`, and `FKIT_BOOTSTRAP_PASSWORD` outside Git and run `./scripts/bootstrap-user.sh`. The command is safe to repeat; after the first user exists it exits without changing accounts. The password is never printed.

For a manual bootstrap, place these three variables in a protected file outside the checkout (for example `/run/secrets/fkit-bi-bootstrap.env`, mode `0600`), then source it only in the current shell with `set -a; . /run/secrets/fkit-bi-bootstrap.env; set +a`, run `./scripts/bootstrap-user.sh`, and `unset FKIT_BOOTSTRAP_USERNAME FKIT_BOOTSTRAP_DISPLAY_NAME FKIT_BOOTSTRAP_PASSWORD` afterward. Do not put credentials in shell arguments, command history, `.env.example`, or Git; use the host's secret manager to create and rotate the protected file.

The bootstrap credentials are passed only to the one-shot `analytics-bootstrap` container. The default Compose network uses `172.29.0.0/24`, with Nginx fixed at `172.29.0.250`; this lets Analytics trust only Nginx's overwritten client-IP header. If that subnet conflicts with the host, choose a free `COMPOSE_SUBNET`, set `PROXY_CONTAINER_IP` to an unused address inside it, and set `FKIT_TRUSTED_PROXY_CIDRS` to that Nginx address with `/32`.

TLS выбирается явно через `TLS_MODE=off` (по умолчанию), `self-signed` или
`public`. В public-режиме `CERTBOT_CHALLENGE=http-01` выпускает один сертификат
с точными SAN `bi.kitexp.ru`, `api.bi.kitexp.ru` и
`generator.bi.kitexp.ru` через общий persistent webroot. Режим
`CERTBOT_CHALLENGE=dns-01` сохраняет прежний apex+wildcard контракт и требует
внешние Yandex Cloud DNS credentials. Оба режима требуют `CERTBOT_EMAIL`.

`bi.kitexp.ru` обслуживает Web и совместимые path-based API;
`api.bi.kitexp.ru` и `generator.bi.kitexp.ru` проксируют исходный URI напрямую в
соответствующий backend. Доменные HTTP-запросы при включённом TLS перенаправляются
на HTTPS, кроме `/.well-known/acme-challenge/`; IP остаётся доступен по HTTP.
Ошибка первого public-выпуска оставляет подготовленный HTTP-контур и завершает
delivery ошибкой — self-signed fallback отсутствует. Grafana привязана только к
loopback и требует непустой `GRAFANA_ADMIN_PASSWORD`; Prometheus и exporters
остаются внутри Compose network. Операторские шаги описаны в
`docs/dev-deployment.md`.
