---
title: 'Epic 3: raw telemetry и realtime state'
type: 'feature'
created: '2026-10-11'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '329f1b268fb1cd9743789844dd0235e6c497b447'
epic_baselines:
  analytics: 'a370a17cc735b206b628d646202ee65a3b75c85b'
  generator: '0a0d85799f93a91b7e57fb1da461225e9f1c4397'
context:
  - '{project-root}/fkit-bi-infra/docs/bmad/implementation-artifacts/epic-3-context.md'
  - '{project-root}/fkit-bi-analytics/AGENTS.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** В Epic 3 нет рабочего контура realtime telemetry: Generator не пишет пакеты, Analytics не хранит raw и durable work, не рассчитывает current signal/state проекции и не отдаёт их через read-контракт. Без полного контура оперативные значения оборудования недоступны.

**Approach:** Выполнить весь Epic 3 связным вертикальным срезом: Analytics владеет схемой, handoff, проекциями, state evaluation/workers и API-контрактами, Generator — валидируемым идемпотентным JDBC writer и передачей сгенерированных измерений. Завершить интеграцией от настроенного оборудования до committed current reads; проверить связный контур после реализации всех историй.

**Always:** Следовать roadmap/acceptance Epic 3 и контрактам raw storage/writer. Raw append-only и typed; пакет атомарен, максимум 1000 measurements, SHA-256 идемпотентность по producer/batch; hints durable и атомарны с raw. UTC-day RANGE partitions, 90-дневный raw retention и 7 будущих дней; maintenance вне write path, без потери данных, нужных активной работе. Проекции читают только committed prepared state, не сканируют raw в API; freshness, quality, dataThrough/calculatedAt и offline semantics явны. Evaluator детерминирован, дедлайны/leases durable, машина имеет один ближайший deadline. Существующая signal_usage повторно не создаётся. Web-код и деплой не входят в работу.

**Never:** Не менять Web-приложение, не деплоить и не настраивать DevOps, не добавлять брокер или PITR/backup (Story 1.5 отложена), не выполнять разрушительные миграции. Не вводить per-row FK/unique/value indexes для raw, default partition, query-time raw scans или неограниченное ожидание на write/maintenance.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Повтор записи | Идентичный producer/batch/hash либо повторное использование id с другим payload | Идемпотентный успех либо конфликт; дублей raw нет | Неопределённый результат повторяется с тем же id |
| Ошибка пакета | Ошибка любой строки/hint/partition lock | Ни header, ни часть raw/hints не зафиксированы | Retryable-конфликт возвращается без частичной записи |
| Старая/некачественная телеметрия | Out-of-range, uncertain/bad, clock skew или stale input | Диагностика сохраняется, но не становится usable current/rule input | Неизвестное правило не выдаёт ложный state |
| Повторная/конкурентная обработка | Hint/job lease занят либо worker упал | Работа повторно арендуется; публикация атомарна | API продолжает отдавать предыдущую committed-проекцию |
| Офлайн и deadline | Нет принятой телеметрии за offlineAfter; rule transition отложен | OFFLINE имеет приоритет; ближайший deadline срабатывает один раз | Worker retry ограничен и не дублирует интервал/событие |

</frozen-after-approval>

## Code Map

- `fkit-bi-analytics/src/main/resources/db/changelog/` — релизы 001–006; добавить versioned-схему raw/work/projection/state, индексы и процедуры.
- `fkit-bi-analytics/src/main/java/ru/fkit/bi/analytics/` — текущие образцы controller/service/repository; новые пакеты telemetry, projection, state реализуют хранение и read API.
- `fkit-bi-analytics/src/test/java/ru/fkit/bi/analytics/migration/FoundationMigrationTest.java` и другие тесты — образцы JUnit5/Testcontainers с PostgreSQL 16.
- `fkit-bi-generator/src/main/java/ru/fkit/bi/generator/telemetry/` — `TelemetryMeasurement`, `TelemetryBatch`, `TelemetrySink`, пустой `JdbcTelemetrySink`; заменить заглушки и встроить запись в имеющийся execution path.
- `fkit-bi-infra/docs/bmad/specs/spec-raw-telemetry-ingestion/{telemetry-storage.md,writer-protocol.md}` — нормативный контракт пакета/hash/партиций/lock; синхронизировать с реализованной схемой.
- `fkit-bi-infra/docs/bmad/specs/spec-mvp-acceptance-strategy/implementation-roadmap.md` и `implementation-artifacts/epic-3-context.md` — критерии и зависимости 3.1–3.6; контракты API для Web принадлежат нашим репозиториям, не Web.

## Tasks & Acceptance

**Execution:**
- [x] Story 3.1 — Миграции/контракты Analytics вводят batch, append-only типизированный raw, hints, registry, партиции и bounded lifecycle routines; переиспользовать signal_usage.
- [x] Story 3.2 — Writer Generator реализует TELEMETRY_BATCH_V1 hash, валидацию, атомарные usage/raw/hints, retry/conflict/drop и метрики.
- [x] Story 3.3 — Durable handoff Analytics упорядоченно объединяет dirty ranges и поддерживает checkpoint, leases, SKIP LOCKED и восстановление после падения.
- [x] Story 3.4 — Analytics асинхронно рассчитывает current/latest-received/usable, freshness и calculation currency; bounded read API отдаёт только committed projection.
- [x] Story 3.5 — Детерминированный типизированный evaluator реализует приоритеты, условия, задержки, hysteresis, default/OFFLINE, интервалы/current state и worker ближайшего deadline.
- [x] Story 3.6 — Связать Generator execution с telemetry-контрактом и пройти путь equipment → raw → projections → current signal/state reads; добавить принадлежащую нам API-документацию для Web-разработчика.
- [x] Добавить/актуализировать тесты схемы/границ, writer idempotency/atomicity, handoff, projection/evaluator/deadline и cross-repository golden slice. После Epic 4 запустить полные тесты Analytics и Generator по запросу пользователя.

**Acceptance Criteria:**
- При корректном batch, который принят или повторён без изменений, запись Generator сохраняет атомарные raw/handoff; повтор не дублирует строки.
- При принятом raw и запуске/перезапуске worker’ов durable work обрабатывается логически один раз и публикует committed signal/state projections.
- При непригодном quality, stale signal, offline machine или отложенном переходе evaluator соблюдает приоритеты Epic3 и не создаёт ложного usable value.
- При чтении current signal/state Analytics API возвращает явные value/freshness/quality/currency из projections без raw scan.
- При настроенном equipment и сгенерированных sample end-to-end Epic3 golden slice показывает принятые измерения и рассчитанное состояние машины через API.
- Если expired partition пересекает pending work или активный lease/publication, retention оставляет нужный raw и выполняется ограниченно с возможностью retry.

## Implementation Notes

Реализованы Analytics releases 007–010: raw batch/measurement/partition registry и lifecycle, durable hints/work/leases, signal current projection/API, state interval/current/deadline schema/API и scheduled workers. Generator получил типизированный batch, TELEMETRY_BATCH_V1 SHA-256, JDBC sink с lock/validation/atomicity/retry/drop/metrics. API-контракт current telemetry/state обновлён в `fkit-bi-analytics/docs/contracts/analytics-api-draft.yaml`; общий storage contract — в `fkit-bi-analytics/docs/contracts/raw-telemetry-v1.md`.

Реализованы Analytics releases 007–010, Generator batch writer и стабильный realtime execution adapter `RealtimeTelemetryExecutionService`. Current signal/state API контракты отражают currency, bounded telemetry reads и truncation. Retention сохраняет last-known current values даже после удаления raw partitions. PostgreSQL upgrade/retention и golden-slice тесты расширены. Общий финальный прогон завершён: Analytics — 62 теста, Generator — 25 тестов, без ошибок.

Story 3.6 использует узкий execution boundary для передачи уже сгенерированного stable-id batch в writer; полное управление Scenario/GenerationRun остаётся Epic 6. Тесты Generator execution-to-storage и Analytics raw-to-current API формируют cross-repository golden slice по общему versioned telemetry contract.

## Spec Change Log
- 2026-10-11 — Пользователь явно расширил авторизованный объём Epic 3, подтвердив завершение Story 3.6. KEEP: Web-код, deployment, backup/PITR и full Scenario/GenerationRun lifecycle не входят; финальный общий тест-прогон выполняется после Epic 4. Для golden slice добавлен стабильный Generator execution-to-writer boundary.

## Review Triage Log

| Finding | Disposition | Evidence / follow-up |
|---|---|---|
| Offline clock used event timestamp rather than receipt time | patched | Evaluator now receives both `observed_at` and `received_at`; added delayed-observation test. |
| Current signal currency conflated `stale` and `recalculating`; current-state omitted currency | patched | Separate pending/retry vs active lease states; current-state API and OpenAPI now expose `dataThrough`, `calculatedAt`, `stale`, `recalculating`. |
| Retention scheduler could starve later expired partitions; partition-window metric counted ensures, not actual ACTIVE partitions | patched | Candidate selection excludes blocked partitions before `LIMIT`; gauge counts ACTIVE registry rows in target window. |
| Removed state rules left runtime rows | patched | Evaluation removes no-longer-configured rule timers. |
| Legacy `signal_usage` timestamp conversion lacks upgrade test | carried / patch | Test-only changelog applies through 006, seeds a prior row, then upgrades through 007 and asserts both timestamps. |
| Retention blocker behavior lacks PostgreSQL behavior test | carried / patch | New upgrade/retention integration test creates an expired partition with retry work, proves retention refuses it, then retires after work clears. |
| Current projection may clear last values after raw retention expires | patched | 009 refresh preserves previous received/usable typed values when no retained raw row exists and marks the usable value stale. |
| Unfiltered current-signal response has no explicit result cap | patched | Current read caps at 500, returns `truncated`, and the OpenAPI contract documents targeted signal filtering. |
| Machine-level currency could overstate slowest signal progress | patched | `dataThrough`/`calculatedAt` aggregate with `min`; any missing active-signal projection marks the response stale. |
| LONG comparison loses precision above 2^53 | patched | Integral comparisons use exact decimal values, including `IN` and bounds. |
| Worker barrier included future partitions | patched | Projection barrier checks only the 90 retained event-time days it can read, not seven future partitions. |
| Accepted counter increments before commit | patched | Writer increments accepted measurement metrics only after `TransactionTemplate` commits; idempotent retries count zero new measurements. |
| Writer's missing machine context permits cross-machine batches | false | Batch intentionally permits multiple machines; each signal's owner is read and durable hints are grouped by that authoritative machine. |
| Work lease can expire during projection | false | Projection transaction timeout is 8s and bounded SQL timeout 6.5s, below the 30s lease. |
| Rule timer deletion can survive failed publication | false | The only caller invokes evaluator inside the projection worker's encompassing transaction, so failed publication rolls timer deletion back. |
| Synchronous realtime retry blocks indefinitely | false | Retry count is bounded to two sleeps (150ms total) and each transaction/query has a timeout; exhausted realtime batches are dropped and counted. |
| Historical late-data state replay absent | deferred to Epic 4 | Historical replay is explicitly owned by Epic 4; current realtime state path does not claim replay. |
| Generator run engine does not invoke the writer; 3.6 end-to-end acceptance absent | patched for Epic 3 boundary | Added a stable-id realtime execution adapter that calls the sink; Generator storage and Analytics projection/API golden tests exercise both sides of the versioned contract. Full Scenario/GenerationRun lifecycle remains Epic 6. |

Independent blind, edge-case, and verification-gap reviews completed against the implementation diff. Epic 4 delivered the remaining historical replay/projection seam and final complete verification passed for both backend repositories.


## Design Notes

Retention должен учитывать будущие таблицы 3.3/4.x, которых пока может не быть в схеме. Миграция 3.1 задаёт проверяемый seam/guard, но не должна ссылаться на несуществующие объекты так, чтобы блокировать чистую установку; решение и доказательство совместимости фиксируются в реализации.

## Verification

**Commands:**
- `./mvnw test` в `fkit-bi-analytics` — ожидаются успешные тесты миграций, handoff, проекций, state и API.
- `./mvnw test` в `fkit-bi-generator` — ожидаются успешные тесты кодирования batch и атомарной JDBC-записи.
