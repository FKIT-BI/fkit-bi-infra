# FKIT BI project context

FKIT BI consists of a web client, Java 21 Spring Boot analytics and generator services, and PostgreSQL. Analytics owns equipment CRUD, analytics, incidents and all Flyway migrations. Generator owns scenarios/runs and writes raw telemetry through `TelemetrySink` using JDBC. Kafka, ETL, production deployment and business UI are out of scope.

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
