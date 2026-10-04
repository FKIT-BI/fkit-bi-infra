# FKIT BI project context

FKIT BI consists of a web client, Java 21 Spring Boot analytics and generator services, and PostgreSQL. Analytics owns equipment CRUD, analytics, incidents and all Flyway migrations. Generator owns scenarios/runs and writes raw telemetry through `TelemetrySink` using JDBC. Kafka, ETL, production deployment and business UI are out of scope.

Read `../architecture/fkit-bi-architecture.md` and `../architecture/fkit-bi-components.md` before planning.

## BOOTSTRAP-001

Status: in progress. Repository skeletons, BMAD 6.12.0, CI and initial Dev delivery.
