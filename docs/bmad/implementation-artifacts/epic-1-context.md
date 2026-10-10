# Epic 1 Context: Secure and reproducible runtime foundation

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Make the MVP stack reproducibly buildable and operable from a clean checkout: an operator can start the services, authenticate, and observe whether they are healthy. This foundation supports subsequent equipment, telemetry, and analytics work. The available planning artifacts contain the implementation roadmap and architecture spine; a separate UX/design artifact is not present for this epic.

## Stories

- Story 1.1: Application foundations
- Story 1.2: PostgreSQL migration ownership
- Story 1.3: Authentication
- Story 1.4: Public edge and observability
- Story 1.5: Backup and restore operations

## Requirements & Constraints

- Verify a clean-checkout build and CI, and provide consistent service health/readiness, an error envelope, and trace ID behavior.
- The migration transition must preserve existing development marker metadata; verify both clean-database and existing-development-database paths with Testcontainers.
- Analytics is the sole schema migration owner. Generator must not report ready until Analytics migrations have succeeded and the exact supported schema release is present.
- Provide bootstrap operator setup/login, user creation, and JWT authentication shared by Analytics and Generator. The MVP has no role/permission matrix: authenticated users share business access.
- The stack must remain usable when observability components are unavailable; metrics and dashboards must not become a service-startup dependency.
- Support access through `bi.kitexp.ru` and the confirmed IP `45.132.176.28`. Route Analytics and Generator APIs by path on the same host; no API/generator subdomains are needed. Development IP access is HTTP; HTTPS-by-IP is not required. Public HTTPS and explicit self-signed dev/demo TLS modes must not silently fall back between modes. Verify IP/domain routes and both TLS modes.
- Provision Prometheus, Grafana, exporters and dashboards; expose monitoring endpoints only on internal networks. Emit JSON logs and propagate trace IDs safely across proxy/service boundaries.
- Keep three daily full custom-format database dumps, restrict dump-file permissions, monitor backup age, and document raw-partition maintenance. Run an isolated restore drill. No PITR or HA in MVP; local backups do not protect against host loss.

## Technical Decisions

- Both Java services use Ports and Adapters; domain/application logic stays independent of HTTP and JDBC adapters. Use Java 21, Spring Boot 3.5.16, Liquibase 4.31.1, PostgreSQL 16, and the managed PostgreSQL JDBC driver 42.7.11.
- Analytics and Generator are separate deployables with separate domain ownership, even though they share PostgreSQL. The infrastructure repository owns Compose/proxy/observability integration; Analytics owns authentication and schema migrations; Generator owns JWT validation and readiness behavior.
- Use one PostgreSQL instance with logical schemas. Analytics owns and applies Liquibase at startup; Generator waits for Analytics readiness. Both services check the exact supported `equipment.schema_release` value. In the test/demo contour, Analytics, Generator, embedded Liquibase, and `postgres_exporter` use one shared database account. Separate least-privilege roles are deferred until production or external customer data.
- Liquibase changesets are immutable after application, explicitly included, and organized as YAML orchestration plus formatted SQL under Analytics resources. Remove the old Flyway bootstrap dependency without discarding existing marker metadata.
- Nginx is the sole public entry point. Route `/api/analytics/` and `/api/generator/` to their respective services. Public TLS uses Certbot DNS-01 with automatically managed temporary Yandex Cloud DNS challenge records; the certificate covers `bi.kitexp.ru` and `*.bi.kitexp.ru`. DNS credentials are deployment secrets, never committed. TLS mode is selected explicitly (`public` or `self-signed`); issuance failure must be visible rather than silently changing modes.
- Keep application, database and monitoring ports private behind the Compose network; only Nginx HTTP/HTTPS is public. Monitoring scrapes and dashboards are internal deployment components, not public API routes.
- Schedule one full logical dump daily and retain only the latest three. Dumps cover the application database, including configuration, retained raw telemetry, projections, incidents, generator scenarios/runs, and Liquibase metadata. They do not contain deployment secrets, TLS keys, monitoring volumes, or cluster roles.
- Retain readiness/schema-release checks even with the shared database account; database-role separation is intentionally not part of this MVP contour.

## Cross-Story Dependencies

- Story 1.1 establishes the service boundaries, configuration, readiness, and response conventions used by the remaining stories.
- Story 1.2 must establish migration ownership and readiness before Generator can safely use the shared schema; Story 1.3 authentication must be integrated in both services.
- Story 1.4 composes both services behind Nginx and adds observability around the runnable stack. Its startup must tolerate observability being unavailable.
- Story 1.5 operates on the database and partition lifecycle established by Story 1.2 and must be verified against the integrated runtime. These stories collectively unblock Epic 2 and later telemetry work.
