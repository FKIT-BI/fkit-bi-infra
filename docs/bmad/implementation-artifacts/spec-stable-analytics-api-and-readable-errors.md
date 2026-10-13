---
title: 'Стабильный Analytics API и понятные ошибки в Web'
type: 'bugfix'
created: '2026-10-13'
status: 'done'
route: 'dispatch'
review_loop_iteration: 1
baseline_commit: '4b30ef130621625bcb8e564c4b04d43512d98ac3'
repository_baselines:
  analytics: 'c54a93b207161b3cfcc19722a75b10e26cbc9c1c'
  web: '65833f9408ecb29cd85bf5c5e234e67c29a1b8b2'
context:
  - fkit-bi-infra/docs/bmad/project-context.md
  - fkit-bi-infra/docs/bmad/planning-artifacts/architecture/architecture-fkit-bi-2026-10-08/ARCHITECTURE-SPINE.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Реальный Analytics API расходится с каноническим контрактом: список причин потерь падает при пустых фильтрах, incidents отклоняет допустимый `limit=500`, live-периоды с будущей границей суток дают 422, а свободный ввод единиц приводит к ошибкам создания машин и сигналов. Ошибки backend технические и непоследовательные, Web повторяет неретраебельные запросы, показывает сырой текст и теряет следующие cursor-страницы.

**Approach:** Выровнять backend и нормативный OpenAPI, затем локально синхронизировать и перегенерировать Web-клиент. Добавить API активных единиц, применить его в формах, централизовать `ErrorResponse`/retry/cursor и покрыть HAR-сценарии тестами.

## Boundaries & Constraints

**Always:** Analytics владеет OpenAPI и Liquibase; `requestedTo` сохраняется, расчёт ограничивается ready boundary с `partial=true`; cursor default/max равен 100/500; Web использует generated types и proxy URL; ошибка содержит безопасный русский текст, точные `fieldErrors` и `traceId`, а backend log — stack trace.

**Never:** Не скрывать backend-дефекты обрезанием периода только на Web; не хардкодить список единиц во frontend; не раскрывать SQL, stack trace, credentials или payload в ответе; не ретраить детерминированные 4xx; не менять формулы аналитики, lifecycle инцидентов или справочники данных.

## I/O & Edge-Case Matrix

| Сценарий | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Loss reasons | Нет optional filters | 200 и страница | Nullable SQL типизирован |
| Incidents | limit нет / 500 / 501 | 100 / успех / 400 | path=`limit`, `OUT_OF_RANGE` |
| Live range | `from < now < requestedTo` | 200, clipped data, исходный `requestedTo`, partial | Неверный диапазон → 400 |
| Unit catalog | GET | Активные code/name/symbol/quantityCode | Структурированная ошибка |
| Machine/signal | Unknown unit либо неполная rate/unit пара | Нет записи | 422 с точным path/code |
| Internal error | Exception | Безопасный 500 + traceId | Stack только в log |
| Cursor UI | >500 incidents | Все страницы без потерь | Abort/error не маскируются |

</frozen-after-approval>

## Code Map

- `fkit-bi-analytics/.../incidents/{IncidentRepository,IncidentService,ManualIncidentController}.java` — loss SQL и cursor limits.
- `fkit-bi-analytics/.../metrics/HistoricalMetricsController.java` — live clipping и metadata.
- `fkit-bi-analytics/.../api/` и модули `machine/signal/component` — error payload и unit validation.
- `fkit-bi-analytics/src/main/resources/db/changelog/` — additive `unit_code VARCHAR(64)` migration.
- `fkit-bi-analytics/docs/contracts/analytics-api-draft.yaml` — канонический Swagger.
- `fkit-bi-web/src/shared/api/`, `src/app/App.tsx`, `src/shared/ui/panel/` — generated client, errors, retry, cursor.
- `fkit-bi-web/src/pages/admin/` и `src/shared/mocks/` — unit selectors, mocks и UI tests.

## Tasks & Acceptance

**Execution:**
- [x] Backend incidents — исправить nullable SQL, limits 100/500 и тесты.
- [x] Backend analytics — clip всех historical reads и elapsed previous period.
- [x] Backend errors/reference — validation mapping, safe 500 logging, units endpoint, unit field errors и migration до 64.
- [x] OpenAPI — units, rate/unit dependency, live semantics, статусы и error examples; усилить contract tests.
- [x] Web API/UI — синхронизировать YAML/types, units query/selectors, cursor loader, formatter и retry; обновить mocks/tests.

**Acceptance Criteria:**
- Given HAR-запросы, when они повторены, then loss reasons/incidents/live dashboard успешны, а неверная единица даёт понятную 422 возле поля.
- Given >500 incidents, when Web загружает журнал, then cursor-страницы объединены без потерь.
- Given 4xx `ApiError`, when React Query его получает, then retry отсутствует; сеть, 429 и ограниченные 5xx ретраятся.
- Given обновлённый OpenAPI, when Web синхронизирован/generated, then backend и frontend проверки проходят.

## Implementation Notes

- Ready boundary = `min(requestedTo, now)`. Вариант с `min(machine_current_state.data_through)` отклонён: одна отстающая ACTIVE-машина обрезала бы live-период всего предприятия, а пустая область давала бы 404. Свежесть данных по-прежнему в `metadata.dataThrough`/`partial`.
- Ошибки диапазона и параметров analytics-чтений — 400 (как в OpenAPI); ошибки полей конфигурации — 422.
- Web: mutations не ретраятся вообще (create машины/сигнала не идемпотентны); queries — ≤2 повтора для сети/429/5xx.
- Web OpenAPI синхронизирован копированием из Analytics, т.к. `npm run api:sync` читает ещё не обновлённый DEV.
- Infra `scripts/test-api-contracts.py`: Analytics 67 → 68 операций.
- Подтверждения: `fkit-bi-analytics/docs/tasks/STABLE-API-001-har-errors.md`, `fkit-bi-web/docs/tasks/WEB-004-stable-api-errors.md`.

## Spec Change Log

- Итерация 2 (retest HAR): шторм `GET incidents` из формы «Ещё идёт» (Date.now() в ключе запроса) и 422 `INVALID_INCIDENT_RANGE` из-за потери миллисекунд `coverageFrom` в `toIso`. Правила времени инцидента не изменены; ошибки инцидента получили поля, причины и `details` границ, форма Web зеркалит правила backend.

## Review Triage Log

- [fixed] Ready boundary по `min(data_through)` ломала «Сегодня» для предприятия с отстающей машиной и давала 404 для пустой области.
- [fixed] `AnalyticsOpenApiContractTest` не знал `listMeasurementUnits`.
- [fixed] Web повторял mutations при 5xx/сетевой ошибке — риск дублей.
- [fixed] Не было клиентской проверки rate>0 и пары rate/unit; неактивная текущая единица терялась в селекторе; ошибка `parameters[i].unitCode` не показывалась у поля.
- [fixed] Field errors Bean Validation были общими (`INVALID`); теперь коды по ограничению. Type mismatch/missing param — 400 с path. Остальные сообщения analytics-контроллера и incidents переведены.
- [fixed] Счётчик операций в infra contract lint.

## Verification

**Commands:**
- `./mvnw verify` (`fkit-bi-analytics`).
- `npm test`, `npm run typecheck`, `npm run lint`, `npm run build` (`fkit-bi-web`).
- `git diff --check` во всех изменённых репозиториях.
- `python scripts/test-api-contracts.py` (`fkit-bi-infra`).

**Результат (2026-10-13):** analytics `mvn -B verify` в Docker JDK 21 — 87 tests, 0 failures; web — 79 tests, typecheck, lint, build пройдены; infra contract lint — 68 операций Analytics. Остаток: деплой на DEV и повтор сценариев HAR (особенно loss-reasons на DEV PostgreSQL и «Сегодня» в +03:00).
