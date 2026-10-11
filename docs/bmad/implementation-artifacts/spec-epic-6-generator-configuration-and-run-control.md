---
title: 'Эпик 6: сценарии Generator и управление запусками'
type: 'feature'
created: '2026-10-11'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '2b79f6515a5cd94666dda922b85c2c6dc107c4b8'
analytics_baseline_commit: '6fdce37fe63a3faa457d83432b942fc6b5a109b6'
infra_baseline_commit: '76477a8b00c6f20460dadfb5e530a5f1c248c3d7'
context:
  - 'fkit-bi-infra/docs/bmad/implementation-artifacts/epic-6-context.md'
  - 'fkit-bi-infra/docs/bmad/project-context.md'
  - 'fkit-bi-generator/AGENTS.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Generator пока умеет только передать готовый telemetry batch в writer; нет сохранённых сценариев, снимков конфигурации, управляемых запусков и воспроизводимого realtime/historical/scheduled выполнения. Поэтому нельзя целостно настроить демонстрационные данные и безопасно запускать/повторять генерацию.

**Approach:** Реализовать Epic 6 единым backend-срезом по каноническим моделям Scenario, signal behavior, GenerationRun и Generator API. Generator хранит собственный домен и пишет raw только через существующий `TelemetrySink`; Analytics владеет миграциями общей БД и единой моделью оборудования. Завершить acceptance-проверкой всех 12 операций и end-to-end поведения генерации.

## Boundaries & Constraints

**Always:** Scenario ссылается на существующие сущности Analytics и не дублирует оборудование. Неполный сценарий сохраняется только `DISABLED`; для активации/запуска выполняется полная проверка. Behavior использует типизированные модели, `baseBehaviors` и один уровень phase override `REPLACE|DISABLE`; `expectedState` служит только диагностикой. Каждый запуск атомарно получает immutable snapshot оборудования и развёрнутых behavior вместе с deterministic seed. Run, progress, reservation и checkpoint долговечны; многомашинное резервирование атомарно. Raw измерения типизированы, имеют event time и передаются batch до 1000 строк через append-only `TelemetrySink`. История использует UTC `[from,to)`, chunks по 5 минут и стабильные batch IDs; realtime пропускает просроченные ticks; scheduled не пишет до заданного instant. `COMPLETED` означает только завершение записи, не готовность Analytics.

**Never:** Не менять Web, не создавать Generator equipment CRUD, повторяющиеся расписания, историю версий Scenario/оборудования, SSE/WebSocket или REST-ingestion raw. Не писать готовые state/KPI/intervals, не создавать partitions/DDL из Generator и не обходить `TelemetrySink`. Не запускать deployment/DevOps-процедуры.

## I/O & Edge-Case Matrix

| Сценарий | Вход / состояние | Ожидаемое поведение | Ошибка |
|---|---|---|---|
| Неполный сценарий | Definition не готов к генерации | Сохраняется `DISABLED`; validation возвращает field-path issues, activation/run запрещены | Стабильный `422` без частичной записи |
| Создание Run повторено | Тот же idempotency key и canonical body | Возвращается исходный Run и тот же snapshot | Изменённый body с ключом — `409 IDEMPOTENCY_KEY_REUSED` |
| Конкурирующий запуск | Общая realtime machine или пересекающийся future/history range | Проверка/резервация всего набора атомарна | `409` с конфликтующими machine/ranges |
| Сбой исторического chunk | Batch частично подтверждены, checkpoint ещё не зафиксирован | Retry повторяет стабильные IDs; подтверждённые batches не дублируются | Нет checkpoint до ACK всех batches |
| Future misfire / stop | Старт опоздал более 30 секунд либо Run остановлен | `SCHEDULE_MISSED` без telemetry; stop не обрывает текущую batch-транзакцию | Терминальный результат и bounded diagnostics |

</frozen-after-approval>

## Code Map

- `fkit-bi-generator/src/main/java/ru/fkit/bi/generator/telemetry/TelemetrySink.java`, `JdbcTelemetrySink.java`, `TelemetryBatch.java`, `TelemetryMeasurement.java`, `TelemetryBatchHasher.java` — существующий типизированный append-only writer, его atomicity, hashing, locks и raw validation; расширять использование, не создавать второй writer.
- `telemetry/RealtimeTelemetryExecutionService.java` и `src/test/java/ru/fkit/bi/generator/telemetry/JdbcTelemetrySinkIntegrationTest.java` — тонкая граница публикации и PostgreSQL/Testcontainers pattern; полноценные clocks/run lifecycle и acceptance ещё отсутствуют.
- `fkit-bi-generator/src/main/java/ru/fkit/bi/generator/{api,auth,health}` — общий error/trace/JWT API boundary и schema readiness; сохранить их conventions.
- `fkit-bi-generator/docs/contracts/generator-api-draft.yaml` — нормативный OpenAPI 3.1 с 12 операциями Scenario/Run; реализовать его без смены operationId и префикса `/api/v1`.
- `fkit-bi-analytics/src/main/resources/db/changelog/db.changelog-master.yaml` и `releases/012-manual-loss-attribution/` — владелец additive Liquibase migration и последний release convention. Таблицы Scenario/Run/checkpoint/reservation принадлежат схеме `generator`, DDL добавляет Analytics; Generator migrations не выполняет.
- `fkit-bi-analytics/src/main/resources/db/changelog/releases/007-raw-telemetry/` и `fkit-bi-analytics/docs/contracts/raw-telemetry-v1.md` — общий batch/storage contract. Equipment/signal readiness читается из существующих Analytics таблиц без синхронного межсервисного вызова.
- Канонические подробности: `fkit-bi-infra/docs/bmad/specs/spec-generator-domain/`, `spec-generator-api-contract/`, `spec-generator-run-execution/`, `spec-raw-telemetry-ingestion/`; тестовые границы и AC-8/9/11 — `spec-mvp-acceptance-strategy/{test-strategy,acceptance-catalog}.md`.

## Tasks & Acceptance

**Execution:**
- [x] Analytics Liquibase release: durable Scenario/Run/snapshot/idempotency/reservation/checkpoint/coverage storage и ownership constraints; сохранить DDL ownership Analytics и append-only raw.
- [x] Generator Scenario domain/API: 6 контрактных операций, typed numeric/counter/boolean/string behavior, validation, readiness, `DISABLED` draft и полная замена definition.
- [x] Generator Run API/domain: snapshot compilation, deterministic seed, idempotent create, pagination/detail, conflicts, state transitions, counters, progress и analytics context.
- [x] Realtime execution: durable reservation, per-signal ticks, no catch-up, bounded batch/flush, stop/failure/retry и stable batch identity через `TelemetrySink`.
- [x] Historical/scheduled execution: 90-day/partition preflight, non-overlap coverage, 5-minute checkpoints, retry-safe chunks, quota/throttling, exact UTC schedule и 30-second misfire.
- [x] Generator OpenAPI/документация и acceptance suite: 12 operation IDs, API/auth/errors, snapshots, races, deterministic data, AC-8/9/11 и сквозной путь raw→Analytics projections/reads. Тесты запускать после реализации всего Epic 6.

**Acceptance Criteria:**
- Given один Enterprise и существующее оборудование, when пользователь сохраняет и активирует Scenario, then ownership, statuses, signal type, phases и behavior валидируются, а API возвращает стабильные field paths без CRUD оборудования в Generator.
- Given Scenario и optional seed, when создаётся Run, then атомарно сохраняются развёрнутый неизменяемый snapshot, детерминированный seed, idempotency result и все нужные reservations; конкурентный конфликт не оставляет частичную резервацию.
- Given realtime run, when ticks задержаны или пользователь выполняет stop/retry, then нет catch-up burst или разрыва текущей batch-транзакции, counters/lifecycle согласованы, а одинаковый batch retry не дублирует raw.
- Given historical или scheduled run, when диапазон выполняется/наступает future instant, then checkpoints и deterministic batches восстанавливают неполный chunk, до срока нет raw, overlap/misfire отклоняется согласно контракту.
- Given весь Epic 6, when выполняется acceptance suite на поддерживаемой PostgreSQL, then все 12 Generator operations, AC-8/9/11, snapshot immutability, reservation races и путь Scenario→Run→raw→Analytics read проходят без изменения Web.

## Implementation Notes

- Additive DDL релиза Analytics `013-generator-run-control` создаёт Scenario, Run, неизменяемый snapshot, idempotency, attempts, reservations, historical capacity, checkpoint и append-only coverage. Составные внешние ключи привязывают Scenario, Run, target Machine, reservation и coverage к одному Enterprise; изменение Run identity/snapshot и подтверждённой historical coverage запрещено.
- Диапазон scheduled reservation — `[scheduledStartAt, reservedTo)`. Если `durationMs`/`eventTo` не переданы, `reservedTo` равен `NULL` (положительная бесконечность), поэтому GiST exclusion запрещает пересекающиеся резервации этой Machine до освобождения при terminal status. Это сохраняет явно разрешённый unbounded Scheduled `LOOP` из API и execution-контракта, несмотря на противоречащую им фразу о bounded reservation в companion по concurrency.
- DDL, владение и append-путь raw telemetry не меняются. Значение поддерживаемого `equipment.schema_release` здесь не обновляется, поскольку его readiness-потребители находятся вне этого migration slice Analytics.
- Realtime execution добавляет lease-based durable worker и checkpointed pending batch; sink возвращает receipt, чтобы Run counters различали committed/duplicate raw batch и dropped realtime batch. Per-signal latest-due tick используется без catch-up, а stop drain ограничен одним batch до 1000 rows.

## Spec Change Log

## Review Triage Log

- `patch` — Historical coverage по ошибке ограничивалась одной записью на Run/Machine; unique constraint допускает отдельные chunk ranges. Проверка 6-минутного Run теперь требует обе 5-минутные coverage-записи; повторная фиксация того же диапазона остаётся идемпотентной.
- `patch` — Realtime executor мог завершить истёкший Run до replay durable pending batch. Pending ACK теперь проверяется до bounded end; acceptance регистрирует запись batch перед `COMPLETED`.
- `patch` — Snapshot compiler применял phase override signal ко всем target machines, хотя definition принадлежит одной машине. Compiler фильтрует overrides по machine ownership; двухмашинная acceptance проверяет отсутствие чужого signal в snapshot.
- `false` — Замечание об отсутствии enterprise membership isolation опровергается утверждённой MVP debt: роль/permission matrix и tenant membership не входят в MVP; все authenticated users разделяют business access.
- `patch` — Нулевой `COUNTER_RATE.resetThreshold` приводил к делению на ноль, а сумма PULSE durations могла переполнить signed long. Scenario validation теперь выдаёт стабильные ошибки до активации; API acceptance проверяет оба входа.
- `patch` — Historical schedule пропускал tick 0 фазы, в отличие от realtime. Cursor теперь использует ceil для нижней границы с разрешённым нулевым tick; crash-recovery acceptance сравнивает повторяемый первый batch.
- `false` — Сохранение исходного `eventTo` при retry соответствует зафиксированному execution contract: retry сохраняет bounded event window и не продлевает исходный Run.
- `patch` — Stop для `QUEUED`/`SCHEDULED` закрывает текущую запись attempt вместе с Run; acceptance проверяет `finished_at` после CANCELLED.
- `false` — `validateRun` сообщает снимок конфликтов, но не резервирует ресурсы; конкурентную атомарность обеспечивает create path транзакционными advisory locks и повторной проверкой, подтверждённой race acceptance.
- `patch` — Непредставимая для PostgreSQL длительность могла доходить до timestamp conversion вместо structured validation. Run validation теперь проверяет верхнюю границу DB timestamp до reservations/estimates; acceptance отправляет `Long.MAX_VALUE` и ожидает 422.
- `false` — Scheduled start в пределах допустимого 30-секундного misfire начинает выполнение немедленно по контракту без catch-up; event time фиксируется worker claim, поэтому запуск в poll time не является отклонением от запрошенной семантики.
- `false` — Исторический первый tick на границе фазы относится к тому же tick schedule, что и realtime tick index 0; он восстановлен отдельной patch-строкой выше, поэтому второе замечание про начало генерации не является дополнительным дефектом.

## Design Notes

Долговечный run-control и telemetry append — разные транзакционные границы: сначала атомарно фиксируются Run, snapshot и reservations; затем каждый подтверждённый batch записывается существующим sink; checkpoint отражает только целиком подтверждённый chunk. При retry сохраняются run identity, snapshot и seed, а writer deduplicates stable batch IDs.

## Verification

**Commands:**
- `./mvnw test` в `fkit-bi-generator` — все unit/API/PostgreSQL acceptance тесты проходят.
- `./mvnw test` в `fkit-bi-analytics` — Liquibase upgrade и raw/projection integration tests проходят на PostgreSQL.
- Проверка OpenAPI Generator: YAML валиден, 12 operationId неизменны, security, request/response schemas и examples согласованы.
- Сквозная acceptance-проверка Epic 6 — realtime/historical/scheduled сценарии фиксированного seed доходят через raw writer до Analytics projections/read API.
