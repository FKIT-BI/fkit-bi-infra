---
title: 'Epic 4: исторические проекции и Analytics API'
type: 'feature'
created: '2026-10-11'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '329f1b268fb1cd9743789844dd0235e6c497b447'
epic_baselines:
  analytics: 'a370a17cc735b206b628d646202ee65a3b75c85b'
context:
  - '{project-root}/fkit-bi-infra/docs/bmad/implementation-artifacts/epic-4-context.md'
  - '{project-root}/fkit-bi-analytics/AGENTS.md'
  - '{project-root}/fkit-bi-infra/docs/bmad/planning-artifacts/analytics-design-notes.md'
  - '{project-root}/fkit-bi-infra/docs/bmad/specs/spec-analytics-projection-storage/projection-storage.md'
  - '{project-root}/fkit-bi-infra/docs/bmad/specs/spec-machine-state-projections/recalculation-process.md'
  - '{project-root}/fkit-bi-infra/docs/bmad/specs/spec-minute-rollups/rollup-model.md'
  - '{project-root}/fkit-bi-infra/docs/bmad/specs/spec-minute-rollups/calculation-rules.md'
  - '{project-root}/fkit-bi-infra/docs/bmad/specs/spec-metric-formulas/metrics-catalog.md'
  - '{project-root}/fkit-bi-infra/docs/bmad/specs/spec-metric-formulas/numeric-examples.md'
  - '{project-root}/fkit-bi-infra/docs/bmad/specs/spec-timeseries-pareto-chronometry/series-models.md'
  - '{project-root}/fkit-bi-infra/docs/bmad/specs/spec-timeseries-pareto-chronometry/losses-and-chronometry.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** После Epic 3 система принимает телеметрию и публикует realtime state, но не имеет durable расчётного контура для истории, минутных агрегатов, производственных метрик и ограниченных исторических read API.

**Approach:** Выполнить Epic 4 как единый Analytics vertical slice: durable dirty-range queue и атомарная публикация, additive minute projections, replay/late-data обработка и bounded API исторических серий, потерь, хронометража, overview и метрик.

## Boundaries & Constraints

**Always:** Расчёты повторяемы и безопасны при at-least-once обработке; входные окна сливаются по машине, выравниваются по UTC minute и захватывают предшествующий state context. До готовности staging readers видят прежний committed результат; замена интервала, currency, checkpoint и job status публикуются атомарно. Rollups содержат additive facts, не ratios; крупная гранулярность собирается из минут. Формулы вычисляются из сумм, учитывают OFFLINE как пробел данных, PLANNED_STOP отдельно, несовместимые units как null. История ограничена 90 днями; ответы сообщают actual bounds, dataThrough, freshness/status и truncation; raw не используется как fallback для API. Очереди используют leases/SKIP LOCKED, границы чтения и worker ресурсов ограничены.

**Never:** Не менять Web-приложение, не деплоить и не менять DevOps, не добавлять broker, отдельные физические rollups выше минуты, silent historical rule versioning, query-time raw scan или частичную публикацию диапазона.

## I/O & Edge-Case Matrix

| Сценарий | Вход / состояние | Ожидаемое поведение | Ошибка |
|----------|-----------------|---------------------|--------|
| Late data во время чтения | Batch старше опубликованного `dataThrough` | Dirty окно помечено; до полной пересборки API отдаёт прежний snapshot с stale/recalculating, затем целиком новый | Повтор batch не удваивает facts; конфликт batch id отклоняется |
| Replay с плохим диапазоном | PERIOD за пределами retention или пустой/inverted интервал | Job не создаётся, API сообщает validation error | Частичные work rows отсутствуют |
| Метрики с неполным coverage | OFFLINE/неполные минуты/несовместимые единицы | Coverage и null-метрики явны; OFFLINE не считается DOWN | Не подменять отсутствующие значения нулями |
| Повтор публикации | Worker завершился до/после commit и lease истёк | Повтор безопасен, читатели видят только старую или новую полную версию | Нет двойного счёта |

</frozen-after-approval>

## Code Map

- `fkit-bi-analytics/src/main/resources/db/changelog/` — releases 001–010 и схемы Epic 3; добавить версии для расчётной очереди, staging, rollups, метрик и replay jobs, не переписывая применённые релизы.
- `fkit-bi-analytics/src/main/java/ru/fkit/bi/analytics/telemetry/` — существующие handoff/work/state projection workers и current read patterns; переиспользовать leases, SQL timeouts и bounded API подход.
- `fkit-bi-analytics/src/main/java/ru/fkit/bi/analytics/` — контроллеры, сервисы и репозитории API; новые calculation, replay и historical read модели должны опираться на committed projections.
- `fkit-bi-analytics/docs/contracts/analytics-api-draft.yaml` и `docs/contracts/README.md` — поддерживаемые backend-to-Web контракты; синхронизировать каждое новое поле/ограничение.
- `fkit-bi-infra/docs/bmad/implementation-artifacts/epic-4-context.md`, analytics design notes и контракты в `docs/bmad/specs/` — нормативные источники формул, границ публикации, response limits и shift semantics.
- `fkit-bi-analytics/src/test/` — текущие Testcontainers/PostgreSQL integration tests; расширить ими migration, queue, atomic publication, rollup formulas, replay и API edge cases. Web репозиторий не трогать.

## Tasks & Acceptance

**Execution:**
- [x] `fkit-bi-analytics/src/main/resources/db/changelog/releases/` и `.../stateprocessing/` — durable per-machine dirty-range discovery/merge, leases, checkpoints и validated staging; обеспечить ограниченный worker и атомарный range publication вместе с currency/status.
- [x] `fkit-bi-analytics/src/main/java/ru/fkit/bi/analytics/` и release migrations — расчёт exact state/effective intervals из контекста до окна, late input и current rules; замена диапазона идемпотентна и сохраняет ручные классификации как отдельный источник.
- [x] `.../aggregation/` и schema — минутные signal numeric, machine metric и loss rollups с quality, min/max/sum/count, counter deltas/resets, duration/output/scrap/events/loss facts; закрывать только полные минуты до `dataThrough`.
- [x] `.../metrics/` и API model — вычислять Availability, Performance, Quality, OEE, MTBF, MTTR по totals и определённым знаменателям; агрегировать enterprise/line/machine без усреднения ratios и проверять совместимость units.
- [x] `.../api/` и `docs/contracts/analytics-api-draft.yaml` — bounded current/overview, historical series, Pareto, chronometry и shift reads; в ответах документировать окна, resolution, coverage, currency, empty/partial/stale и truncation; 90-day limit, максимум 1000 metric/loss points и 720 telemetry points.
- [x] `.../replay/` и API contract — durable PERIOD/ALL replay lifecycle, validation, progress/status, cancellation/retry semantics; правила применяются текущие, replay не запускается неявно при чтении.
- [x] `fkit-bi-infra/docs/bmad/implementation-artifacts/sprint-status.yaml` и эта спецификация — Epic 3/4 implementation завершена после единого полного прогона Analytics и Generator.

**Acceptance Criteria:**
- Given обычный или late telemetry input, when очередь обработана повторно/параллельно, then dirty окна объединяются, контекст состояния восстановлен, а committed диапазон заменён полностью без двойных фактов.
- Given опубликованные minute projections, when запрашивается период или несколько машин, then метрики рассчитываются из сумм с формулами и правилами coverage/units, совпадая с нормативными числовыми примерами.
- Given historical API запрос, when он укладывается в 90-day и point limits, then возвращаются фактические границы, минуты/series/shift metadata и качество публикации без raw scan; превышение лимитов явно отклоняется или truncates согласно контракту.
- Given PERIOD/ALL replay, when диапазон валиден, then durable job показывает прогресс и после публикации заменяет весь диапазон атомарно; невалидный запрос не создаёт job.
- Given worker failure, late batch или replay в процессе, when читатель обращается к API, then он видит только предыдущую или новую полную committed проекцию и корректный stale/recalculating state.

## Implementation Notes

Реализацию вести только в Analytics и backend API-документации. Stories 4.1–4.7 исполняются связанным блоком; unit/integration/e2e тесты можно добавлять одновременно с кодом, но команды проверки не запускать до завершения всех семи stories и Epic 3. Целевые API latency/worker lag из контекста — acceptance goals, но полноценный нагрузочный benchmark остаётся Epic 7.

## Spec Change Log

## Review Triage Log

- blind-hunter — `false`: OpenAPI уже описывает operations current/overview, historical metrics, losses, chronometry и state intervals; проверены пути раздела `paths` около строк 888–1122.
- blind-hunter — `false`: список recalculation jobs поддерживает cursor/status в контракте и реализации; claim опровергают схема query-параметров и `ReplayService.list`.
- blind-hunter — `false`: устаревшее описание Epic 3 обновлено: исторический replay и staging обозначены работой Epic 4, полный сценарий Generator остаётся Epic 6.
- blind-hunter — `false`: открытый последний state interval ожидаем при достижении replay до `dataThrough`; worker расширяет период до текущего `dataThrough`, а API представляет действующее состояние интервалом с `to=null`.
- blind-hunter — `medium`: лимит replay ранее не включал carry-in raw events, позволяя обойти заявленный bounded reconstruction; подсчёт теперь охватывает весь retained context и только ACTIVE signals.
- blind-hunter — `medium`: validation ранее проверяла partition coverage без синхронизации с удалением partitions; validation и replay теперь берут shared advisory xact locks на весь диапазон.
- blind-hunter — `medium`: реконструкция ранее читала события удалённых/неактивных сигналов; оба event-запроса теперь фильтруют `status='ACTIVE'`.
- blind-hunter — `false`: out-of-range quality counter намеренно сохраняется независимо от usability; спецификация качества различает исходное качество и пригодность измерения.
- blind-hunter — `medium`: можно было активировать несколько COUNTER-сигналов с одной production/scrap семантикой и удвоить агрегаты; сервис теперь атомарно сериализует конфигурацию машины и отклоняет конфликт.
- blind-hunter — `false`: actual bounds, partial/currency и truncation присутствуют в ответах серий; запросы за будущие границы отвергаются валидацией.
- edge-case-hunter — `false`: summary поддерживает shiftId вместе с from/to отдельной веткой, а также shiftDate; обе формы проверены в `OperationsReadController`.
- edge-case-hunter — `medium (unverified)`, `defer`: если неполный набор effective intervals существует, gaps могут не получить fallback state; подтвердить/опровергнуть после добавления Epic 5 ручных overlay-классификаций и теста смешанной timeline.
- edge-case-hunter — `medium (unverified)`, `defer`: loss reason и ручные classifications не входят в автоматически вычисляемые Epic 4 rollups; проверить объединение ручных инцидентов и автоматических фактов в Epic 5.
- edge-case-hunter — `medium`: lifecycle не имел cancellation endpoint, хотя контракт требует cancellation semantics; добавлен DELETE только для PENDING job, состояние CANCELLED и освобождение ссылки на queued work.
- verification-gap — `medium`: не было DB-backed проверки исторических rollups и query APIs; golden-slice теперь проводит ingest → worker → rollup, series, metric, state interval и chronometry на PostgreSQL.
- verification-gap — `medium`: не было DB-backed проверки replay lifecycle; golden-slice теперь проверяет durable PENDING job, cancellation и успешную worker publication с очисткой staging.

## Design Notes

Публикация должна иметь чёткий boundary: длительное чтение raw, reconstruction и staging не удерживают транзакцию активных таблиц; короткая транзакция меняет полный диапазон и currency/checkpoint/job state. Replay PERIOD/ALL и автоматическая late-data обработка используют один вычислительный путь.

## Verification

**Commands:**
- `mvn -B -Dmaven.repo.local=/m2/repository test` в контейнере Maven/Java 21 для `fkit-bi-analytics` — PASS, 62 tests, 0 failures/errors/skips (2026-10-11).
- Та же команда для `fkit-bi-generator` — PASS, 25 tests, 0 failures/errors/skips (2026-10-11).
