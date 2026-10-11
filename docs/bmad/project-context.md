# FKIT BI project context

FKIT BI consists of a web client, Java 21 Spring Boot analytics and generator services, and PostgreSQL. Analytics owns equipment CRUD, analytics, incidents and all Liquibase migrations. Generator owns scenarios/runs and writes raw telemetry through `TelemetrySink` using JDBC. Kafka, ETL, production deployment and business UI are out of scope.

Read `../architecture/fkit-bi-architecture.md` and `../architecture/fkit-bi-components.md` before planning.

## BOOTSTRAP-001

Status: complete (2026-10-04). Все четыре репозитория имеют успешные GitHub CI;
analytics, generator и web образы опубликованы и доставлены. Infra SHA
`f08d8eb8004538f70e7b4c04fbfb553a0d02a287` доставлен точной ревизией. Публичные
`/`, `/api/analytics/actuator/health` и
`/api/generator/actuator/health` проверены с HTTP 200; backend health вернул UP.
Delivery работает через `develop` и host-wide lock, сохраняет private `.env` и
PostgreSQL volume. Подробные run IDs и актуальные SHA записаны в
`docs/dev-deployment.md`.

Публичный edge использует три точных имени: `bi.kitexp.ru` для Web и совместимых
path-based API, `api.bi.kitexp.ru` для Analytics и
`generator.bi.kitexp.ru` для Generator. Текущий Dev rollout использует
Certbot HTTP-01 с общим persistent webroot и exact-SAN сертификатом; DNS-01
apex+wildcard остаётся опциональным режимом. При TLS доменный HTTP перенаправляется
на HTTPS, ACME challenge остаётся на HTTP, а доступ по IP сохраняется по HTTP.
