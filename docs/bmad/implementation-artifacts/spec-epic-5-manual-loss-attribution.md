---
title: 'Эпик 5: ручная классификация потерь и проекции'
type: 'feature'
created: '2026-10-11'
status: 'done'
route: 'dispatch'
baseline_commit: '299f2e70fc2f5c59196b96f9664c7600421ab5b6'
infra_baseline_commit: 'd3580f5957b8dc906fd651e2350de3d33d0da2d7'
review_loop_iteration: 0
context:
  - 'fkit-bi-infra/docs/bmad/implementation-artifacts/epic-5-context.md'
  - 'fkit-bi-infra/docs/bmad/specs/spec-loss-reasons-incidents/SPEC.md'
  - 'fkit-bi-analytics/AGENTS.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Проблема:** Analytics пока не позволяет вести каталог причин потерь и ручные инциденты; заготовленные таблицы проекций не отражают ручные state/reason overlays, поэтому история, Pareto и хронометраж не показывают атрибуцию.

**Подход:** Реализовать Epic 5 целиком в Analytics: каталог причин, lifecycle ManualIncident, атомарно согласованные effective-state/metric/loss projections и сквозные golden acceptance tests по канонической аналитической спецификации и API-контракту.

**Always:** Analytics владеет кодом, миграциями и контрактом БД; Web не меняем. Интервалы полуоткрытые `[from,to)`, границы UTC и не будущие. ManualIncident не меняет raw telemetry или calculated `machine_state_interval`. State-effect и reason-effect overlap валидируются независимо. Reason применяется только к эффективным `IDLE`, `DOWN`, `SETUP`, `PLANNED_STOP`; `RUN/OFFLINE` не классифицируются. Мутации инцидентов атомарно сохраняют dirty work на объединение старого и нового диапазона; опубликованные effective intervals, metrics и losses заменяются согласованно и безопасно при повторе.

**Never:** Не удалять физически причины/инциденты, не менять исторические факты задним числом при отключении причины, не вводить несколько причин/автоклассификацию, не переписывать calculated state/raw, не реализовывать Web, deployment, DevOps или отложенный Backup/Restore.

## I/O & Edge-Case Matrix

| Сценарий | Вход / состояние | Ожидаемое поведение | Ошибка |
|---|---|---|---|
| Создание причины | Enterprise, уникальные code/name, category | Создана ACTIVE причина; отключение сохраняет её исторические ссылки | Дубликат/чужой Enterprise — стабильный 409/404 |
| Изменение причины | Категория уже использовалась инцидентом | Разрешены display-поля; category/code/enterprise неизменны после использования | Запрет защищён сервисом и БД |
| Пересечение эффектов | State-only + reason-only либо повторный эффект того же вида | Независимые эффекты совмещаются; дублирующийся эффект отклонён | 409 с отдельным кодом overlap |
| Нет eligible loss | Reason-only интервал не пересекает готовый eligible state | Запись отклонена; готовность читается по `dataThrough` | 409 `INCIDENT_HAS_NO_LOSS_INTERVAL` |
| Потерян ответ POST | Повтор `Idempotency-Key` с тем же/другим body | Тот же результат либо конфликт при повторном использовании ключа | 409 `IDEMPOTENCY_KEY_REUSED` |
| Асинхронная публикация | Dirty work ещё выполняется | API отдаёт старую полную проекцию с freshness/recalculating metadata; после commit доступны новые интервалы, bucket и Pareto | Никакого частично опубликованного диапазона |

</frozen-after-approval>

## Code Map

- `fkit-bi-analytics/docs/contracts/analytics-api-draft.yaml` — нормативный Analytics API v1; операции LossReason около 228–322, incident — около 1162–1316, DTO далее в `components/schemas`. Реализовать операции и согласовать недостающие error/response детали здесь, не меняя Web.
- `fkit-bi-infra/docs/bmad/specs/spec-loss-reasons-incidents/` — канонические модели, lifecycle, overlaps и атрибуция; при расхождении использовать эти решения и зафиксировать контрактное исправление.
- `fkit-bi-analytics/src/main/resources/db/changelog/releases/011-historical-projections/001-historical-projections.sql` — существующие effective interval, metric/loss buckets и staging; `db.changelog-master.yaml` подключает новые versioned migration releases.
- `fkit-bi-analytics/src/main/java/ru/fkit/bi/analytics/aggregation/MinuteProjectionService.java` — staging и swap minute projections. Сейчас рассчитанные интервалы копируются без overlays, reason равен null; расширить существующую публикацию, не ломая retry-safe замещение.
- `telemetry.TelemetryWorkRepository`, `telemetry.SignalProjectionWorker`, `telemetry.HistoricalStateReplayService` — durable lease/dirty work, worker transaction и историческое восстановление. Использовать существующую очередь, не создавать параллельный transient queue.
- `metrics/HistoricalMetricsController.java`, `telemetry/OperationsReadController.java` — чтение loss/chronometry/current DTO; сейчас reason display возвращается null. Обогатить из каталога и сохранить freshness semantics.
- `src/test/java/ru/fkit/bi/analytics/telemetry/TelemetryGoldenSliceTest.java`, `src/test/java/ru/fkit/bi/analytics/migration/` — примеры integration/golden и миграционных тестов. Добавить целевые incident и loss API acceptance tests.
- `fkit-bi-infra/docs/bmad/implementation-artifacts/sprint-status.yaml` — ключ `5-1-loss-reason-catalog`; перевести Epic 5/story statuses по фактическому завершению.

## Tasks & Acceptance

**Execution:**
- [x] Analytics incident module, additive Liquibase migration, DB constraints/indexes and repositories — обеспечить tenant ownership, стабильные идентификаторы, мягкое отключение/отмену, ссылки на причины, transactional idempotency records и durable work.
- [x] LossReason API/service/DTO — CRUD/list filters по контракту; уникальность code и нормализованного name в Enterprise; category из закрытого enum и неизменность после первого назначения; DISABLED исключён из нового назначения, но доступен в истории.
- [x] ManualIncident API/service/repository — create/list/get/update/close/soft cancel и Enterprise journal; проверки machine/enterprise ownership, периода, coverage/dataThrough, эффекта, reason status и независимых overlaps; POST idempotency + атомарный dirty-range union.
- [x] Расширить effective timeline staging — разрезать calculated интервалы границами state/reason incidents, сохранять calculated/effective state, источник и incident/reason refs; учитывать underlying OFFLINE и reason eligibility.
- [x] Вместе с effective intervals строить machine metrics/loss buckets; в одной публикации заменять затронутый диапазон трёх проекций и завершать durable work. Сохранить prior committed данные во время пересчёта.
- [x] Реализовать loss reason display в Pareto, timeseries, state intervals, chronometry и применимых current reads; обеспечить `UNCLASSIFIED`, `OTHER`, clipping/shift metadata, pagination и limit согласно v1 контракту.
- [x] Golden acceptance tests Epic 5, включая AC-6: потерянный ответ и retry, идемпотентность, ошибочные ownership/overlap/coverage, закрытие/cancel/update, future eligibility ongoing annotation, RUN/OFFLINE exclusion, late/replay пересчёт и атомарность read projections. Обновить task evidence в `fkit-bi-analytics/docs/tasks/` и sprint status.

**Acceptance Criteria:**
- Given Enterprise, when создаются причины с повторяющимся code или нормализованным name, then конкурентно существует не более одной записи на соответствующий ключ.
- Given использованная или отключённая причина, when её изменяют/назначают, then запрещённые поля и новые назначения отклоняются, а старые инциденты/история остаются читаемыми.
- Given два инцидента, when эффекты перекрываются, then конфликтуется только повторное пересечение того же измерения; state-only и reason-only могут совпасть по времени.
- Given incident mutation, when запрос фиксируется, then incident, идемпотентный результат и minute-aligned dirty range сохраняются атомарно; одинаковый retry не создаёт дубликаты.
- Given dirty range, when worker публикует результат, then effective timeline, metric buckets и reason buckets соответствуют одним границам состояния/причины и становятся видны атомарно; исходные raw/calculated интервалы неизменны.
- Given исторический или текущий read, when интервал содержит допустимый reason, then API возвращает reason и incident reference; RUN/OFFLINE не классифицируются, null представлен как unclassified, freshness корректно сообщает незавершённый пересчёт.
- Given весь Epic 5, when выполняется acceptance suite, then все сценарии API, projection refresh и AC-6 проходят на мигрированной PostgreSQL.

## Implementation Notes

Планировать один additive release для каталога, инцидентов, idempotency и ограничений; новые индексы/constraints должны соответствовать существующим миграционным соглашениям. Проверить взаимодействие incident dirty work с текущей state replay очередью: публикация должна читать актуальные source intervals и не терять generation, пришедший во время stage. Уточнить OpenAPI только там, где реально отсутствует обязательная семантика; сохранить все operationId и маршрутный префикс `/api/v1`.

## Review Triage Log

- blind-hunter — `medium`: ongoing reason-only incident мог начинаться после `dataThrough`, если в source timeline оставался открытый интервал; добавлена проверка `from < dataThrough` и PostgreSQL API regression test.
- blind-hunter — `false`: update/close отменённой записи не снимает `cancelledAt` и не возвращает её эффекты; контракт запрещает восстановление, но не запрещает редактировать сохранённую cancelled-запись.
- blind-hunter — `false`: `author` намеренно является необязательным непроверенным display value; это прямо закреплено в `manual-incident-model.md`, авторизация не заявлена как identity mapping.
- blind-hunter — `false`: при совпавшем hash идемпотентный повтор возвращает уже сохранённый успешный результат согласно контракту retry после потери ответа; другой payload получает `409`.
- blind-hunter — `false`: очередь не теряет рост покрытия — `TelemetryWorkRepository.claim` расширяет `dirty_to` до текущего `dataThrough` перед stage; чтение самой границы в enqueue не приводит к пропуску новых данных.
- blind-hunter — `low`, отклонено: смена Enterprise у оборудования не поддерживается API; замечание требует рассматривать прямую административную модификацию БД/будущего writer и добавлять дополнительный trigger для недостижимого обычным потоком состояния.
- blind-hunter — `low`, отклонено после исправления: reason summary повторно загружался для каждого сегмента; добавлен request-local cache по `lossReasonId` в chronometry и state-intervals, поэтому повторяющиеся сегменты одного reason больше не выполняют повторный запрос.
- blind-hunter — `medium`: replay тест проверял metric/loss buckets, но не повторно опубликованные интервалы; добавлены проверки сегментов и `reasonIncidentId` в effective timeline после replay.
- blind-hunter — `low`: тестов cursor paging не было; добавлены проверки отдельных страниц без повторов и отклонения некорректного cursor.
- blind-hunter — `medium`: evidence-файл утверждал, что PostgreSQL тесты не запускались, хотя полный запуск состоялся; task evidence обновлён по результатам прогона и review.
- edge-case-hunter — `medium`: конкурентные POST с одним ключом на разные machine могли одновременно пройти lookup и столкнуться на unique constraint; добавлена транзакционная advisory-lock сериализация principal/operation/key и проверка повторного ключа на другой машине.
- edge-case-hunter — `medium`: disable причины могло пересечься с её assignment между проверкой статуса и insert/update; create/update блокируют reason row, как и операция смены статуса.
- edge-case-hunter — `medium`: одновременный повтор запроса с тем же ключом имел гонку уникальности; устранён той же advisory-lock сериализацией ключа до чтения и записи idempotency результата.
- verification-gap — `medium`: golden test не подтверждал отображение reason в read API; добавлены assertions для current-state, operations overview, state-intervals и chronometry.

## Design Notes

Расчёт остаётся детерминированной функцией исходной calculated timeline плюс активные ручные overlays. Сначала применяются state overrides, затем reason annotations; reason для строки определяется только на eligible effective-state сегментах. Dirty range изменения — minute-aligned union прежнего/нового интервала, а ongoing end ограничивается `dataThrough`; после публикации дальнейший рост dataThrough снова применяет открытый incident. Это сохраняет существующий подход Analytics: длительные расчёты вне короткого publication transaction, readers видят старую либо новую целую версию.

## Verification

**Выполненная проверка:**
- Полный PostgreSQL-backed Analytics suite выполнен после всех исправлений в Docker с Java 21 командой `./mvnw test`: 67 тестов, 0 ошибок, 0 падений. До полного прогона целевые `ManualLossAttributionApiTest` и `TelemetryGoldenSliceTest` также прошли: 5 тестов, 0 ошибок, 0 падений.
- OpenAPI YAML успешно разбирается; все 65 прежних `operationId` сохранены. `git diff --check` проходит.

## Итог реализации и проверки

- Реализованы каталог причин, lifecycle ручных инцидентов, эффективные state/reason overlays, атомарная публикация interval/metric/loss проекций и обогащение historical/current reads; миграция добавляет ограничения владения, независимых пересечений и идемпотентности. Назначение синхронизировано с блокировкой строки причины, idempotency retry — с транзакционной блокировкой principal/operation/key; ongoing reason-only incident требует старта строго до `dataThrough`.
- Golden/API acceptance покрывают retry потерянного POST-ответа и конфликт повторного ключа, включая повтор на другой машине; проверяют reason summary и `reasonIncidentId` в current-state, operations overview, state-intervals и chronometry, а также изменённую effective timeline после late replay. Создание/изменение инцидента сериализуется по строке причины с изменением её статуса, а поиск/сохранение POST idempotency сериализуется транзакционной блокировкой по principal/operation/key.
- Полный PostgreSQL-backed Analytics suite в Docker с Java 21: 67 тестов, 0 ошибок, 0 падений. OpenAPI YAML разобран, 65 `operationId` сохранены; `git diff --check` пройден.
- Вне набора не запускались генерация клиентов и отдельная внешняя contract-validation команда; deployment и проверки Web не входят в этот scope.
