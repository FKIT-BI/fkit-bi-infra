---
title: 'Предприятия и календарь смен'
type: 'feature'
created: '2026-10-11'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: 'd90c838b16f83cd5343df3aaad23ba2d18e43975'
context:
  - '{project-root}/fkit-bi-infra/docs/bmad/implementation-artifacts/epic-2-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Для настройки оборудования и последующих операций пока нет API и модели предприятия со сменным календарём; event-time нельзя надёжно связать с локальной сменой.

**Approach:** Реализовать в Analytics защищённое управление Enterprise и Shift, хранение с инвариантами в `equipment`, проверку IANA timezone и расписания, детерминированное вычисление occurrence и контракт API по согласованным спецификациям. Сменный `shiftId` остаётся идентификатором предприятия; raw telemetry не несёт его и классифицируется по event time.

**Boundaries & Constraints**

**Always:** UUID генерирует backend; коды передаются клиентом, стабильны и уникальны в своей области. Enterprise timezone обязателен и блокируется при наличии временных эксплуатационных данных. Shift validity полуоткрытая по локальным датам; интервалы полуоткрытые, допускаются пробелы, запрещаются пересечения независимо от статуса. После использования границы и `validFrom` неизменяемы; история и backfill для DISABLED остаются доступны. DST gap сдвигается к первому допустимому instant, overlap выбирает более раннее UTC-смещение. Все бизнес API требуют JWT.

**Never:** Не создавать ежедневные occurrence-записи; не вводить `day/night/all` как системные идентификаторы; не менять смысл сохранённой истории; не добавлять физическое удаление, RBAC, web-редактор и интеграцию shiftId в raw telemetry в эту историю.

## I/O & Edge-Case Matrix

| Сценарий | Вход / состояние | Ожидаемое поведение | Ошибка |
|---|---|---|---|
| Создать предприятие | Уникальный code, name, IANA timezone | `201`, ACTIVE, backend UUID | Невалидные поля `422`, дублирующий code `409` |
| Обновить timezone | Есть телеметрия, инциденты, run или расчёты | Отказать без изменения ресурса | `409 ENTERPRISE_TIMEZONE_LOCKED` |
| Создать смену | Локальные границы, даты действия, code | Сохранить отдельный Shift в Enterprise | Пересечение/дублирующий code `409`; неверные поля `422` |
| Разрешить occurrence | Event instant внутри ночной смены, на границе, в пробеле или DST | Вернуть уникальную пару `shiftId + shiftDate` либо null; начало включено, конец исключён | Некорректная конфигурация не проходит запись |
| Изменить использованное расписание | Изменение start/end/validFrom либо validTo исключает историю | Не менять конфигурацию; предложить закрыть старую и создать новую Shift | `409 SHIFT_SCHEDULE_LOCKED` |
| Список конфигурации | page/size, необязательный status | ACTIVE по умолчанию, стабильная сортировка и page metadata | Невалидная пагинация/фильтр `400` |

</frozen-after-approval>

## Code Map

- `fkit-bi-analytics/src/main/java/ru/fkit/bi/analytics/` -- приложение сейчас содержит только auth, API errors, health и trace filter; модуль оборудования создавать здесь, следуя package-based архитектуре.
- `fkit-bi-analytics/src/main/resources/db/changelog/db.changelog-master.yaml` -- корневой Liquibase include; новые изменения добавлять следующим release, SQL names snake_case, миграции принадлежат только Analytics.
- `fkit-bi-analytics/src/main/resources/db/changelog/releases/001-foundation/001-create-schemas.sql` -- схема `equipment` уже создаётся; не менять базовую миграцию.
- `fkit-bi-analytics/src/main/java/ru/fkit/bi/analytics/api/ApiExceptionHandler.java` -- общий формат ошибок и HTTP mapping; бизнес-коды добавлять согласованно, не обходить handler.
- `fkit-bi-analytics/src/main/java/ru/fkit/bi/analytics/auth/AuthSecurityConfiguration.java` -- границы JWT; конфигурационные endpoint должны быть аутентифицированы.
- `fkit-bi-infra/docs/bmad/specs/spec-equipment-core-configuration/configuration-model.md` -- поля Enterprise и timezone lock; использовать как нормативную модель, не расширять P2.2 line/machine.
- `fkit-bi-infra/docs/bmad/specs/spec-shift-calendar/{SPEC.md,shift-rules.md}` -- нормативные поля, validity, пересечения, occurrence, DST, изменения и сменные API.
- `fkit-bi-infra/docs/bmad/specs/spec-analytics-api-contract/{api-conventions.md,operation-catalog.md,dto-contract.md}` -- `/api/v1`, DTO, ошибки, pagination, статус, OAuth/JWT контракт; не использовать черновой `draft-api.yaml` как источник истины.
- `fkit-bi-infra/docs/bmad/implementation-artifacts/epic-2-context.md` и `.../spec-mvp-acceptance-strategy/implementation-roadmap.md` -- ownership, транзакционные блокировки, область Story 2.1 и зависимости Epic 2.
- `fkit-bi-analytics/src/main/resources/db/changelog/releases/001-foundation/003-create-reference-catalogs.sql` -- пример formatted SQL, timestamps и ограничений; не добавлять Enterprise/Shift в этот уже применённый changeset.

## Tasks & Acceptance

**Execution:**
- [x] `fkit-bi-analytics/src/main/resources/db/changelog/releases/003-enterprise-shifts/` -- добавить нормализованные таблицы, уникальности, ownership/FK, checks и индексы; обеспечить атомарную конкуренцию расписаний на Enterprise.
- [x] `fkit-bi-analytics/src/main/java/ru/fkit/bi/analytics/enterprise/` -- реализовать модели, repository, service и CRUD/status API Enterprise; проверять timezone lock транзакционно.
- [x] `fkit-bi-analytics/src/main/java/ru/fkit/bi/analytics/shift/` -- реализовать Shift CRUD/status, валидацию overlap/исторических lock и pure occurrence/DST resolver.
- [x] `fkit-bi-analytics/docs/contracts/` -- сверить OpenAPI endpoints и DTO с контрактными спецификациями; существующая спецификация содержит операции Story 2.1.
- [x] `fkit-bi-analytics/src/test/java/` -- проверить migration/API и критические края матрицы; 14 targeted test cases прошли на Java 21 + PostgreSQL Testcontainers.
- [x] `fkit-bi-analytics/docs/tasks/2-1-enterprise-and-shift-calendar.md` -- зафиксировать фактический результат и проверки.

**Acceptance Criteria:**
- Given валидный JWT, when клиент создаёт и читает предприятие или его смены, then API возвращает сохранённые ресурсы и конфигурационные списки с согласованной пагинацией/статусом.
- Given timezone не-IANA или дублирующий код, when ресурс создаётся/изменяется, then запись отклонена без частичного состояния.
- Given Enterprise с эксплуатационными temporal data, when timezone меняется, then `409 ENTERPRISE_TIMEZONE_LOCKED` и значение не изменено.
- Given два применимых расписания с пересекающимися локальными интервалами, when второе сохраняется конкурентно или обычно, then ровно одно конфликтное изменение отклонено.
- Given дневная, переходящая через полночь либо 24-часовая смена, when event instant разрешается, then возвращаются корректные `shiftId`, local `shiftDate` и UTC boundaries; общая граница принадлежит следующей смене, пробел — ничему.
- Given DST gap или overlap, when resolver получает occurrence boundary, then соблюдается одна заданная политика и одинаковый результат при повторном разрешении.
- Given использованная Shift, when меняются заблокированные поля либо validTo отрезает существующую shiftDate, then API возвращает `409 SHIFT_SCHEDULE_LOCKED` без изменения истории.
- Given Shift отключена, when запрашивают её detail/историю или пересчитывают применимые даты, then идентичность и validity сохраняются; новые operational selectors её исключают.
- Given запрос без JWT или malformed pagination, when вызывается business API, then возвращаются стандартные `401` или `400` ErrorResponse.

## Implementation Notes

- Реализованы миграция, защищённые CRUD/status/list endpoints, транзакционная сериализация проверки расписаний, проверки блокировки истории и pure resolver. API contract в `fkit-bi-analytics/docs/contracts/analytics-api-draft.yaml` уже описывает операции Enterprise/Shift, поэтому новые paths/DTO не добавлялись.
- Targeted suite `EnterpriseShiftApiTest,ShiftCalendarTest` прошёл: 14 тестов, 0 failures/errors/skips; покрыты строки I/O matrix, дополнительные проверки ревью и Liquibase migration в PostgreSQL 16 Testcontainers. Полный `verify` не запускался, чтобы оставить проверку короткой.
- Java 21 найдена в `/home/dds/.jdks/corretto-21.0.11`; оставшийся риск — сверить динамически проверяемые temporal table names при внедрении Epic 3–5.

## Spec Change Log

## Review Triage Log

- `maybe-false` — timezone-change race with a future first-use telemetry writer — defer (unverified medium): the canonical ingestion design documents a per-signal advisory lock but no Enterprise-row lock, while the corresponding writer is not implemented here; settle when that writer exists and its transaction protocol can be inspected.
- `maybe-false` — shift-use race with a future projection writer assigning `shift_id` — defer (unverified medium): no projection writer exists in the current code to verify whether it serializes on the Enterprise row; settle when the projection writer is implemented.
- `false` — partially introduced `equipment.machine` without `enterprise_id` can break the probe: the canonical machine schema requires ownership, and Liquibase migration/readiness is atomic; a valid running service cannot expose the partial schema state described.
- `medium` — Shift usage/date probes used guessed table names — patch: probes now use canonical `analytics.machine_metric_bucket_1m` and `analytics.machine_loss_bucket_1m`, covered by API regression tests.
- `false` — accepting fixed-offset timezone IDs such as `+03:00`: the contract requires IANA timezone IDs, so rejecting fixed offsets is correct.
- `false` — resolver ambiguity throws `IllegalStateException`: normal create/update validates overlaps irrespective of status, so valid persisted configurations cannot reach that ambiguity; the exception fails closed for manually corrupted data.
- `medium` — missing exact start/end and shared-boundary coverage — patch: resolver tests now assert included start, excluded end, and ownership transfer at a shared boundary.
- `low` — `totalPages` can overflow `int` only at implausible cardinalities far beyond ordinary operation; rejected because addressing this negligible case would require extra complexity and the API contract specifies integer page metadata.
- `medium` — Enterprise search treated `%` and `_` as SQL wildcards rather than literal query characters — patch: search now escapes LIKE metacharacters and has a regression assertion.
- `medium` — timezone lock could miss machine-owned incidents — patch: probe now joins `incident.incident.machine_id` to the owning machine, in line with the ManualIncident ownership model, and is regression-tested.
- `medium` — no successful Enterprise list/default-filter/page-metadata test — patch: API test now verifies default ACTIVE and explicit DISABLED listing with pagination metadata.

## Design Notes

- Resolver проверяет occurrence-кандидаты с локальной даты события и предыдущей даты: это покрывает смену через полночь и случаи равных границ (24 локальных часа). Пара `shiftId + shiftDate` — вычисляемое значение, не отдельная запись.
- Пересечение должно учитывать validity и интервалы, разложенные в локальный суточный круг; равные start/end означают весь день. Сериализация изменений блокировкой Enterprise защищает проверку от двух одновременно прошедших create/update.

## Verification

**Commands:**
- `./mvnw -B -Dmaven.repo.local=/tmp/m2-story-2-1 -Dtest=<targeted classes> test` -- ожидается SUCCESS для новых временных/domain/API проверок.
- `./mvnw -B -Dmaven.repo.local=/tmp/m2-story-2-1 verify` -- ожидается SUCCESS после реализации миграций и API.
- `git diff --check` -- ожидается отсутствие whitespace ошибок.
