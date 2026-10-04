# FKIT BI project context

FKIT BI consists of a web client, Java 21 Spring Boot analytics and generator services, and PostgreSQL. Analytics owns equipment CRUD, analytics, incidents and all Flyway migrations. Generator owns scenarios/runs and writes raw telemetry through `TelemetrySink` using JDBC. Kafka, ETL, production deployment and business UI are out of scope.

Read `../architecture/fkit-bi-architecture.md` and `../architecture/fkit-bi-components.md` before planning.

## BOOTSTRAP-001

Status: in progress. Репозитории и BMAD 6.12.0 подготовлены; BOOTSTRAP-001
может быть завершён только после подтверждённых GitHub CI и фактической Dev
delivery exact infra SHA с public и API healthchecks. Infra delivery использует
`develop`, host-wide lock и не меняет private `.env`, volume или сервисные image
references.
