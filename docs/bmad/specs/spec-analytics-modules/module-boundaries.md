# Владение модулями и зависимости

## Analytics application

| Package module | Владеет | Публичная граница |
|---|---|---|
| `identity` | Users, bootstrap, login/JWT validation для Analytics | Auth/User application services |
| `equipment` | Enterprise, Shift, Line, Machine, Component, Signal, StateRule | Configuration/readiness services |
| `telemetry` | Packet validation, raw batch write, current signal projection | `TelemetrySink.writeBatch` и current-signal queries |
| `stateprocessing` | Durable dirty work, deadlines, state evaluation, intervals and rollups | Recalculation/use-case ports и read projections |
| `incidents` | LossReason, ManualIncident, manual state intervals | Incident/state-override commands |
| `analyticsquery` | Read-only assembly of prepared projections | Analytics HTTP query services |
| `maintenance` | Partition horizon, retention, technical cleanup | Scheduled operational tasks |

## Generator application

| Package module | Владеет | Публичная граница |
|---|---|---|
| `scenarios` | GenerationScenario, typed behaviors, validation and snapshots | Scenario control application services |
| `runs` | Reservations, queue, execution, checkpoints, progress and recovery | Generator Run application services |
| `telemetrysink` | Batched append to Analytics raw telemetry contract | `writeBatch` client/repository boundary |

Generator reads approved equipment and signal configuration from shared PostgreSQL read access; it writes its own `generator` data and appends through the agreed telemetry contract only. Liquibase changes for every schema remain owned by Analytics.

## Dependency and persistence rules

```text
HTTP adapter → application service → domain policy → module-owned repository port
```

- Cross-module calls use an explicitly named application port/DTO; one module cannot import another module’s repository package.
- Repository implementations stay inside the owning module. Cross-module SQL is forbidden except documented multi-table transaction boundaries.
- Shared code is limited to UUID/time/error/result primitives and generated transport contracts; it does not become a second domain-model library.
- Spring `@Transactional` is applied at the use-case boundary. Approved same-database atomic workflows may touch multiple schemas: telemetry batch+raw+first-use/hint, incident mutation+dirty work, staged projection publication.
- No transaction holds while waiting on another service, scheduler, user, or remote DNS/API call.

## Runtime coordination

- MVP runs one Analytics instance and one Generator instance per deployment.
- Durable jobs, calculation leases, generator reservations and `SKIP LOCKED` claims are the source of coordination; process-local locks/caches are optimizations only.
- Existing database leases keep work safe if a second instance is introduced, but multi-instance deployment is not a launch requirement.
- Scheduler and calculation/maintenance workers are hosted in Analytics; Generator workers are hosted in Generator. Their failure does not block API reads or telemetry insertion beyond documented resource limits.
