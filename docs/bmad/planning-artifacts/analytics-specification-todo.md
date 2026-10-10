# FKIT BI — TODO подробной аналитической спецификации

Статус документа: активный рабочий реестр.

Цель: последовательно закрыть доменные, вычислительные, пользовательские и контрактные решения для `fkit-bi-analytics` и связанного с ним `fkit-bi-generator`, после чего собрать подробную спецификацию, достаточную для декомпозиции и начала реализации.

Связанные материалы:

- `analytics-design-notes.md` — журнал уже принятых решений и рабочих предложений.
- `fkit-bi-analytics/docs/contracts/draft-api.yaml` — пример потребностей существующего Web-интерфейса, но не обязательный контракт.
- `docs/architecture/fkit-bi-architecture.md` — исходная архитектурная концепция.
- `docs/architecture/fkit-bi-components.md` — исходные границы приложений и данных.

## Как работать с этим TODO

Для каждого пункта выполняется один и тот же цикл:

1. Зафиксировать пользовательскую или системную цель.
2. Уточнить термины, акторов, предусловия и границы MVP.
3. Описать основной поток, альтернативы и ошибки.
4. Определить доменные сущности, поля, связи и инварианты.
5. Определить влияние на расчёты, SQL, модули и API.
6. Разобрать спорные варианты и принять одно решение.
7. Записать примеры и проверяемые критерии приёмки.
8. Оформить согласованный связный блок отдельным компактным пакетом `docs/bmad/specs/spec-<slug>/`.
9. Обновить `analytics-design-notes.md`, связать пакет с этим реестром и отметить закрытые пункты.

Правила структуры:

- один пакет спецификации охватывает один связный блок решений и не пытается описать всю систему;
- `SPEC.md` содержит цели, возможности, ограничения, критерии успеха и открытые вопросы;
- подробные модели, таблицы правил и примеры выносятся в небольшие companion-файлы внутри того же пакета;
- TODO не дублирует содержание спецификаций, а служит реестром статусов и незакрытых вопросов;
- пакет считается согласованным после ответа на его открытые вопросы и проверки согласованности с соседними пакетами.

Обозначения:

- `[ ]` — не закрыто;
- `[x]` — решение полностью согласовано и перенесено в рабочую спецификацию;
- `DECIDED` — уже есть базовое решение, но детализация пункта ещё не завершена;
- `PROPOSED` — есть рабочее предложение, требующее подтверждения;
- `OPEN` — решение ещё не принято.

## Реестр блочных спецификаций

| Блок | Пакет | Состояние | Осталось согласовать |
|---|---|---|---|
| Идентичность и жизненный цикл оборудования | `docs/bmad/specs/spec-equipment-identity-lifecycle/` | Согласовано | — |
| Иерархия оборудования | `docs/bmad/specs/spec-equipment-hierarchy/` | Согласовано | — |
| Базовая конфигурация оборудования | `docs/bmad/specs/spec-equipment-core-configuration/` | Согласовано | — |
| Календарь смен | `docs/bmad/specs/spec-shift-calendar/` | Согласовано | — |
| Телеметрические сигналы | `docs/bmad/specs/spec-telemetry-signal/` | Согласовано | — |
| Сырая телеметрия и ingestion | `docs/bmad/specs/spec-raw-telemetry-ingestion/` | Согласовано | Retention вынесен в E13/A04 |
| Качество и актуальность сигналов | `docs/bmad/specs/spec-signal-quality-freshness/` | Согласовано | — |
| Декларативные правила состояния | `docs/bmad/specs/spec-machine-state-rules/` | Согласовано | — |
| Проекции и перерасчёт состояния | `docs/bmad/specs/spec-machine-state-projections/` | Согласовано | — |
| Ручные SETUP/PLANNED_STOP overlays | `docs/bmad/specs/spec-manual-state-overrides/` | Согласовано | Full Incident/LossReason lifecycle остаётся P14/P15 |
| Каталог состояний машины | `docs/bmad/specs/spec-machine-state-catalog/` | Согласовано | Полные metric formulas остаются G14 |
| Минутные агрегаты MVP | `docs/bmad/specs/spec-minute-rollups/` | Согласовано | Каталог и назначение LossReason остаются P14/P15 |
| Формулы производственных показателей | `docs/bmad/specs/spec-metric-formulas/` | Согласовано | DTO и формат warnings остаются P20 |
| Timeseries, Pareto и Chronometry | `docs/bmad/specs/spec-timeseries-pareto-chronometry/` | Согласовано | — |
| Причины потерь и ManualIncident | `docs/bmad/specs/spec-loss-reasons-incidents/` | Согласовано | Authentication обязателен; `author` остаётся непроверенным display value, полный audit вне MVP |
| Нагрузочный профиль и SLO MVP | `docs/bmad/specs/spec-mvp-load-slo/` | Согласовано | Фактические пределы подтвердить benchmark при реализации |
| Observability и runtime | `docs/bmad/specs/spec-observability-runtime/` | Согласовано | Реализовать Compose, instrumentation и provisioned dashboards |
| Домен генератора | `docs/bmad/specs/spec-generator-domain/` | Согласовано | Сложная межсигнальная физика вне MVP |
| Выполнение Generator Run | `docs/bmad/specs/spec-generator-run-execution/` | Согласовано | Контракт реализуется по OpenAPI и runtime specs |
| Generator API contract | `docs/bmad/specs/spec-generator-api-contract/` | Согласовано | Реализовать controller/application boundary по OpenAPI |
| Физическое хранение аналитических проекций | `docs/bmad/specs/spec-analytics-projection-storage/` | Согласовано | — |
| Транзакции и идемпотентность | `docs/bmad/specs/spec-transaction-idempotency/` | Согласовано | — |
| Конкурентность сервисов | `docs/bmad/specs/spec-concurrency/` | Согласовано | — |
| Границы MVP и акторы | `docs/bmad/specs/spec-mvp-scope/` | Согласовано | Проверить demo acceptance в M01/M02 |
| Глоссарий и время | `docs/bmad/specs/spec-domain-time-glossary/` | Согласовано | Формулы и examples остаются в M01 |
| Безопасность, JWT и TLS | `docs/bmad/specs/spec-security-audit/` | В работе | Уточнить JWT endpoints/defaults и provisioning secrets |
| Модульные границы Analytics/Generator | `docs/bmad/specs/spec-analytics-modules/` | Согласовано | Java package structure переносится в implementation skeleton |

## Definition of Done аналитической фазы

- [ ] Все пункты этого TODO либо закрыты, либо явно вынесены за границы MVP.
- [ ] Для каждой сущности определены назначение, поля, типы, обязательность, связи, уникальность и жизненный цикл.
- [ ] Для каждого пользовательского потока определены основной сценарий, альтернативы, ошибки и результат.
- [ ] Формулы показателей однозначны и проверены на числовых примерах.
- [ ] Определены event time, актуальность, late data, history backfill и future scheduling.
- [ ] Определены исходные, производные и агрегированные данные, их владельцы и сроки хранения.
- [ ] Определены транзакционные границы и правила идемпотентности.
- [ ] Сформированы итоговые SQL-модель и OpenAPI-контракты analytics и generator.
- [ ] Определены нефункциональные требования и нагрузочный профиль MVP.
- [ ] Сформированы критерии приёмки, тестовые сценарии и трассировка требований.
- [ ] Набор блочных спецификаций проверен как единое целое и готов к декомпозиции на epics/stories.

---

# A. Основание и границы проекта

## A01. Границы MVP и результат демонстрации

Статус: `DECIDED`.

- [x] Главная ценность — показать end-to-end от конфигурации оборудования и сырых измерений до готовых актуализируемых read models.
- [x] Обязательные flows: настройка, генерация realtime/history/scheduled, current/historical analytics, ручной инцидент и перерасчёт.
- [x] Обязательные качества стенда: durable конфигурация/jobs, корректные расчёты, JWT, TLS, восстановление worker и мониторинг; demo-only: физическая точность сигналов и объём до нагрузочного профиля.
- [x] Out of scope: RBAC, Kafka, ETL, ML/прогнозирование, hardware protocols, автоматическая классификация причин и multi-region HA.
- [x] Критерий успеха и обязательная demo-цепочка определены.

Результат: `docs/bmad/specs/spec-mvp-scope/`.

## A02. Акторы и права действий

Статус: `DECIDED`.

- [x] Конфигуратор, оператор, аналитик и пользователь генератора — UX-персоны без RBAC; обычные authenticated users равноправны.
- [x] Bootstrap account создаётся оператором и только он добавляет пользователей; это единственное выделенное право MVP.
- [x] Определить системных actors: scheduler, Generator, telemetry writer, calculation workers и maintenance worker.

Результат: actor map в `docs/bmad/specs/spec-mvp-scope/actors-and-demo-scenarios.md`.

## A03. Глоссарий и единые правила времени

Статус: `DECIDED`.

- [x] Определить производственные и аналитические термины в одном глоссарии.
- [x] Разделить event time, ingest time, projection currency, effective boundaries и worker detection time.
- [x] Зафиксировать UTC-compatible `TIMESTAMPTZ(3)`, API ISO-8601 date-time с offset и elapsed duration в миллисекундах.
- [x] IANA timezone Enterprise, локальную `shiftDate` и DST gap/overlap использовать по общей политике смен.
- [x] Диапазоны/интервалы полуоткрытые `[from,to)`.

Результат: `docs/bmad/specs/spec-domain-time-glossary/`.

## A04. Нагрузочный профиль и SLO

Статус: `DECIDED`, блок согласован.

- [x] Зафиксировать nominal inventory: 1 предприятие, до 4 линий, 20 машин и до 15 активных сигналов на машину.
- [x] Зафиксировать средний период 10 секунд и nominal поток около 30 measurements/s.
- [x] Утвердить sustained 200 measurements/s, burst 1000/s на 60 секунд и historical 1000–2000/s с throttling.
- [x] Хранить raw 90 суток, а intervals/aggregates — весь срок demo-данных.
- [x] Утвердить SLO current/overview, аналитических API и lag готовых проекций.
- [x] Определить обязательный benchmark на полном стенде 4 vCPU/8 GB с observability.

Результат: `docs/bmad/specs/spec-mvp-load-slo/`.

---

# B. Архитектура и владение данными

## P01. Архитектура системы и внутренние модули

Статус: `DECIDED`.

Уже принято: package-based modular monolith, ownership, ports, cross-module transaction seams, worker hosting и coordination описаны в `docs/bmad/specs/spec-analytics-modules/`.

- [x] Утвердить список модулей Analytics и Generator.
- [x] Определить ответственность и application ports.
- [x] Запретить межмодульный доступ к private repositories.
- [x] Определить направление зависимостей и минимальную shared code policy.
- [x] Определить application ports и data ownership как seams будущего физического разделения.
- [x] Разместить scheduler/workers внутри owning application с durable PostgreSQL work.
- [x] MVP запускает один instance каждого приложения; durable leases/claims сохраняют координацию, если позднее понадобится второй.

Результат: `docs/bmad/specs/spec-analytics-modules/`.

## B02. Одна PostgreSQL и логические области данных

Статус: `DECIDED`, transaction boundaries согласованы; backup/restore остаётся deployment readiness task.

- [x] Утвердить логические схемы PostgreSQL либо отказаться от схем в пользу префиксов таблиц.
- [x] Определить владельца Liquibase и порядок применения миграций.
- [x] Определить роли БД и разрешения analytics/generator.
- [x] Cross-schema транзакции разрешены только для явно описанных atomic use cases; сетевых вызовов внутри транзакции нет.
- [x] Определить правила ссылочной целостности между core, telemetry, analytics, incidents и generator.
- [ ] Определить стратегию backup/restore и удаления старых raw-партиций для MVP.

Результат: data ownership matrix и правила доступа к БД.

---

# C. Доменная модель оборудования

## P02. Иерархия оборудования

Статус: `DECIDED`, требуется детализация.

Уже принято: Enterprise владеет линиями и машинами; свободная Machine может быть однократно назначена ProductionLine; Machine владеет деревом Component и сигналами.

- [x] Утвердить кардинальности и обязательность связей.
- [x] Не вводить жёсткий бизнес-лимит глубины конечного дерева; запрещать циклы.
- [x] Запретить перенос линии, машины и компонента между владельцами; разрешить смену родителя внутри машины.
- [x] Не хранить историческую структуру: при изменении родителя история отображается через текущее дерево.
- [x] Не выполнять физическое удаление; восстановление выполняется переводом из `DISABLED` в `ACTIVE` после проверки.
- [x] Представлять Sensor и Instrument значениями `Component.kind`, а не отдельными сущностями.

Результат: ER-модель оборудования и список инвариантов.

## P03. `ACTIVE` / `DISABLED`

Статус: `DECIDED`.

Уже принято: конфигурационные сущности используют только `ACTIVE` и `DISABLED`.

- [x] Утвердить список сущностей со статусом.
- [x] Определить значение статуса каждой сущности.
- [x] Не вводить `effectiveStatus`: хранить и возвращать только собственный статус сущности.
- [x] Статус действует на саму сущность и не каскадируется; readiness и новые runs отдельно проверяют required dependencies.
- [x] Активный generator run продолжает работу по снимку; новые запуски с `DISABLED`-сущностью запрещены.
- [x] Конфигурационные списки по умолчанию возвращают ACTIVE; DISABLED выбирается явно, операционные selectors скрывают disabled, historical/detail по ID остаются доступны.
- [x] Физическое удаление конфигурации запрещено в MVP; сущности сохраняются в `DISABLED`.

Результат: state transition table и invariants статусов.

## P04. Enterprise

Статус: `DECIDED`, базовая модель согласована.

- [x] Определить окончательный набор полей Enterprise.
- [x] Решить, нужен ли стабильный `code` и правила его изменения.
- [x] Определить уникальность name/code.
- [x] Определить обязательность timezone и допустимые значения.
- [x] Описать create/get/list/update/status flows.
- [x] Определить возможность нескольких предприятий в одном развёртывании.
- [x] Определить последствия изменения timezone.

Результат: модель, команды, запросы и acceptance examples Enterprise.

## P05. Shift

Статус: `DECIDED`, блок согласован.

Уже принято: смены принадлежат предприятию; API использует `shiftId`; `day/night` не зашиты в enum.

- [x] Определить поля Shift.
- [x] Определить правила пересечения, пробелов и полного покрытия суток.
- [x] Определить ночную смену и локальную дату смены.
- [x] Определить влияние DST и смены timezone.
- [x] Определить возможность изменения смен при существующей истории.
- [x] Определить, как выбирать смену в summary, timeseries и chronometry.
- [x] Определить inactive/disabled shift semantics.

Результат: shift calendar rules и примеры границ.

## P06. ProductionLine

Статус: `DECIDED`, базовая модель согласована.

- [x] Определить окончательный набор полей Line.
- [x] Использовать стабильный `code`, отдельный от UUID.
- [x] Определить уникальность имени/кода внутри предприятия.
- [x] Определить автоматическое назначение и изменение `sortOrder`.
- [x] Определить правила переноса линии между предприятиями.
- [x] Определить влияние disabled-линии на машины и аналитику.
- [x] Описать create/get/list/update/status flows; отдельный reorder endpoint не требуется.

Результат: модель и пользовательские потоки ProductionLine.

## P07. Machine

Статус: `DECIDED`.

Уже принято: одна текущая конфигурация без истории версий; полная валидация и атомарное сохранение.

- [x] Определить минимальный и полный набор полей машины.
- [x] Решить, нужен ли стабильный `code`.
- [x] Определить уникальность inventory number и machine code.
- [x] Определить смысл и единицы `nominalRate`.
- [x] Использовать общий ограниченный типизированный `parameters` из C10; отдельная per-machine JSON-схема не нужна.
- [x] Определить атомарную семантику обновления базовых полей.
- [x] Изменения и отключение Machine не влияют на активный generator run, работающий по снимку.
- [x] Разрешить однократное назначение свободной Machine линии; не поддерживать перенос и снятие с линии.
- [x] Полная readiness возвращает весь список стабильных validation issues и повторно выполняется атомарно при переходе в `ACTIVE`.

Результат: aggregate boundary Machine, команды и validation matrix.

## P08. Component и ComponentKind

Статус: `DECIDED`.

- [x] Утвердить расширяемый начальный каталог `ComponentKind` с `OTHER`.
- [x] Использовать стабильный `code`, уникальный внутри Machine.
- [x] Использовать общую модель display-параметров C10 без особых схем на каждый `ComponentKind`.
- [x] Определить дерево, порядок, перемещение внутри Machine и защиту от циклов.
- [x] Использовать `LOGICAL_GROUP` для логических групп; остальные виды описывают физические узлы.
- [x] Не вводить отдельный component health в MVP.
- [x] Отключение Component не каскадируется; потомки, Signals и StateRules сохраняют собственные статусы. Readiness/run validation выявляют отключённую необходимую зависимость; текущий Run продолжает работу по snapshot.

Результат: модель Component и примеры деревьев оборудования.

## P09. TelemetrySignal

Статус: `DECIDED`, блок согласован.

- [x] Определить окончательный набор полей сигнала.
- [x] Утвердить `valueType` для MVP.
- [x] Утвердить `semanticType` и возможность CUSTOM.
- [x] Определить единицы измерения и правила их изменения.
- [x] Определить nullable `expectedIntervalMs` и `staleAfterMs`; частота generator задаётся отдельно.
- [x] Не вводить `requiredForState`: декларативные правила явно ссылаются на сигналы.
- [x] Не хранить протокольный `sourceAddress` в домене; сопоставление принадлежит generator/adapter.
- [x] Определить допустимые изменения сигнала после появления raw data.
- [x] Ограничить MVP низкочастотной телеметрией не быстрее 1 Hz; waveform вынести за scope.
- [x] Зафиксировать пакетный ingestion, асинхронный расчёт и чтение frontend из подготовленных проекций.

Результат: signal catalog model и validation rules.

## C10. Типизированные параметры

Статус: `DECIDED`, блок согласован.

- [x] Machine и Component имеют до 100 встроенных display-параметров без самостоятельного lifecycle.
- [x] Использовать discriminator-типы STRING/NUMBER/BOOLEAN со строго типизированным scalar value.
- [x] Разрешить unitCode только числовому параметру; сортировать по sortOrder и code.
- [x] Хранить manufacturer/model/commissioningYear и nominalRate/productionUnit явными полями Machine.
- [x] Запретить ссылаться на generic parameters из StateRules, формул и аналитических filters; хранить валидированным JSONB.

Результат: parameter model и правила использования параметров.

---

# D. Состояния и правила

## P10. Декларативная модель StateRule

Статус: `DECIDED`, блок согласован.

Уже принято: правила являются исполняемой декларативной структурой, а не текстом.

- [x] Утвердить типизированный AST `ALL/ANY/NOT/COMPARE` и операторы.
- [x] Ссылаться на signals по UUID `signalId` внутри той же Machine.
- [x] Определить unique `priority`, activation/release delay и hysteresis через enter/exit conditions.
- [x] Определить трёхзначную логику TRUE/FALSE/UNKNOWN.
- [x] Преобразовывать NO_DATA/STALE/unusable signal input в UNKNOWN.
- [x] Использовать настраиваемый `defaultState`, default `IDLE`.
- [x] Проверять системный `OFFLINE` до пользовательских rules.
- [x] Выбирать единственный rule по priority и delay; higher priority может preempt.
- [x] Различать event-time `effectiveFrom` и processing-time `detectedAt`.
- [x] Определить полную валидацию, limits AST и validate endpoint.
- [x] Подготовить семь сквозных примеров.

Результат: формальная DSL, evaluator semantics и examples.

## D11. Каталог состояний машины

Статус: `DECIDED`, блок согласован.

- [x] Подтвердить `RUN`, `IDLE`, `DOWN`, `PLANNED_STOP`, `SETUP`, `OFFLINE`.
- [x] Дать бизнес-определение каждого состояния.
- [x] Классифицировать `IDLE/DOWN/SETUP` как разные виды потерь; `PLANNED_STOP` как excluded time; `OFFLINE` как data gap.
- [x] Определить planned/unplanned и productive/operating classification.
- [x] Не ограничивать user transitions; определить failure/recovery и системный OFFLINE.
- [x] Не вводить MachineState `UNKNOWN`; использовать `evaluationQuality=DEGRADED` и блокировать невалидную конфигурацию.

Результат: state catalog и transition semantics.

## D12. Изменение правил без версий конфигурации

Статус: `DECIDED`.

Уже принято: в MVP хранится только текущая конфигурация; повторный расчёт использует текущие правила.

- [x] После изменения rules пересчитать current; historical PERIOD или ALL явно задаёт пользователь.
- [x] Во время перерасчёта отдавать старую committed projection с `recalculating=true`.
- [x] Сохранять предыдущий результат до атомарной staging-подмены нового.
- [x] После первого raw блокируются value type, signal kind, semantic и unit; изменение физического смысла требует нового Signal и отключения старого.
- [x] Replay выбранного периода использует текущую конфигурацию; прежний смысл rules восстановить нельзя.

Результат: `spec-machine-state-projections/recalculation-process.md` и `spec-telemetry-signal/signal-model.md`.

---

# E. Сырая телеметрия

## P11. Raw telemetry contract

Статус: `DECIDED`, блок согласован; retention вынесен в E13/A04.

Уже принято: generator пишет сырые показания; analytics вычисляет официальные состояния; raw append-only.

- [x] Выбрать batch header + типизированные measurement rows; не использовать JSONB frames.
- [x] Определить packet-level identity и idempotency key без уникальности каждой measurement.
- [x] Определить `observedAt`, нормализованный `receivedAt`, producer и sequence.
- [x] Определить отдельные `DOUBLE/LONG/BOOLEAN/STRING` колонки.
- [x] Определить `GOOD/UNCERTAIN/BAD` и compact validation flags.
- [x] Определить атомарную короткую транзакцию пакета без partial success.
- [x] Определить late/out-of-order/future data validation и запрет предварительной записи scheduled future.
- [x] Минимизировать PostgreSQL constraints/indexes горячей raw-таблицы; не использовать FK и per-measurement unique.
- [x] Партиционировать raw по UTC-суткам `observedAt`; срок retention вынести в E13/A04.
- [x] Определить JDBC batch и отдельную квоту/throttling historical import.
- [x] Защищать повторную отправку ключом `(producerId, producerBatchId)`.
- [x] Зафиксировать best-effort degradation: ограниченное ожидание/retry и наблюдаемая потеря raw вместо остановки сервиса.

Результат: SQL telemetry contract и writer protocol.

## E12. Качество и актуальность сигналов

Статус: `DECIDED`, блок согласован.

- [x] Утвердить GOOD/UNCERTAIN/BAD и compact validation flags.
- [x] Отсутствующее измерение означает отсутствие строки; `null`-значения не принимаются.
- [x] Использовать последнее usable `GOOD` значение до `staleAfterMs`, затем передавать `UNKNOWN`.
- [x] Не вводить required-флаг: каждый сигнал из `StateRule` обязан иметь `staleAfterMs`.
- [x] Определить `OFFLINE` до правил по отсутствию любой telemetry дольше `offlineAfterMs`, default 60 секунд.
- [x] Возвращать frontend last received, last usable, `NO_DATA/FRESH/STALE`, quality и calculation currency.

Результат: quality and freshness semantics.

## E13. Raw retention и очистка

Статус: `DECIDED`, блок согласован.

- [x] Хранить raw telemetry 90 суток.
- [x] Удалять только истёкшие UTC-day partitions вне ingestion transaction.
- [x] Не удалять partition до закрытия пересекающихся dirty windows и публикации зависимых intervals/rollups.
- [x] Использовать detach/drop whole partition; не выполнять построчный `DELETE` hot raw.
- [x] После очистки запретить полный перерасчёт удалённого диапазона, сохранив чтение опубликованной аналитики.

Результат: `docs/bmad/specs/spec-mvp-load-slo/load-profile.md` и обновлённый `spec-raw-telemetry-ingestion/telemetry-storage.md`.

---

# F. Расчётный процесс и производные данные

## P12. Производные модели

Статус: `DECIDED`, логическая и физическая модели согласованы.

- [x] Утвердить `signal_current_value` с last received и last usable значениями.
- [x] Утвердить отдельную текущую проекцию состояния машины (`machine_current_state` — рабочее SQL-имя).
- [x] Утвердить хранение истории отдельными интервалами (`machine_state_interval` — рабочее SQL-имя).
- [x] Определить поля и ключи current/interval projections; SQL-индексы уточнить нагрузочным тестом.
- [x] Использовать один последний open interval с `effectiveTo=null`, ограниченный `dataThrough` для history/rollup.
- [x] Обеспечить ровно одно state без дыр и пересечений внутри published coverage.
- [x] Публиковать исправленный диапазон через validated staging и короткую MVCC-транзакцию.
- [x] Разделить signal freshness и calculation currency; использовать `calculatedAt`, `dataThrough`, `stale`, а `recalculating` уточнить в pipeline/API.

Результат: exact state projection model.

## P18. Вычислительный конвейер внутри analytics

Статус: `DECIDED`.

- [x] После commit обнаруживать новые ingest batches и группировать диапазоны по Machine.
- [x] Captured/published checkpoints защищают идемпотентную публикацию.
- [x] Нормализовать dirty windows по UTC-минутам и coalesce на Machine.
- [x] Realtime dirty windows имеют приоритет; user/history work durable и выполняется при доступной квоте, не вытесняя realtime ingestion и query workload.
- [x] Использовать expiring per-machine calculation lease.
- [x] Разрешить независимый parallelism разных machines через `SKIP LOCKED`.
- [x] Расширять слева до устойчивого evaluator context, справа — до current dataThrough.
- [x] Готовить intervals в staging и атомарно заменять active range; aggregates уточнить отдельно.
- [x] Failed user job можно запустить заново; общую dead-letter policy уточнить в operations.
- [x] Crash до publication не меняет active projection; истёкший lease разрешает повтор.
- [x] Несколько instances используют lease и `FOR UPDATE SKIP LOCKED`.

Результат: processing state machine и sequence diagrams.

## P19. Realtime, historical и future event time

Статус: `DECIDED`, блок согласован.

Уже принято: нужны realtime, historical и scheduled generation; analytics работает по event time.

- [x] Realtime пропускает overdue ticks без catch-up burst; future skew остаётся 5 секунд.
- [x] Ограничить realtime future skew настраиваемым порогом, по умолчанию 5 секунд.
- [x] Не записывать scheduled future telemetry заранее; после старта использовать realtime protocol.
- [x] Разбивать historical generation на пятиминутные event-time chunks и batches до 1000 rows.
- [x] Dirty windows массовой загрузки объединяет analytics pipeline независимо от generator checkpoint.
- [x] `COMPLETED` означает завершение raw generation; готовность аналитики определяется отдельно по Analytics `dataThrough`.
- [x] Использовать bounded realtime buffer с ограниченным retry и наблюдаемым drop при перегрузке.
- [x] Выделить historical writer отдельную квоту; throttling/pause/failure не вытесняет realtime и query workload.

Результат: `docs/bmad/specs/spec-generator-run-execution/`.

---

# G. Агрегаты и бизнес-метрики

## P13. Архитектура rollup

Статус: `DECIDED`, минутный контур MVP согласован.

- [x] Использовать единственный базовый и физический бакет `1m`.
- [x] Не создавать `1h` и `1d` в MVP; добавить их только по результатам нагрузочного теста.
- [x] Определить numeric `signal_numeric_rollup_1m`; отдельный STATE/BOOLEAN rollup в MVP не создавать.
- [x] Определить `machine_metric_bucket_1m` с аддитивными durations, quantities и transition counts.
- [x] Определить `machine_loss_bucket_1m` по состоянию и nullable причине для быстрого Pareto.
- [x] В demo MVP выравнивать исторический ответ по закрытым минутам и возвращать фактические границы; не читать raw для неполных краёв.
- [x] Не выполнять rollup propagation в MVP.
- [x] Публиковать полный пересчитанный диапазон короткой атомарной заменой из staging без отдельных revision.
- [x] Агрегировать line/enterprise из machine buckets по текущей структуре; перенос Machine между линиями в MVP запрещён.
- [x] Query API всегда использует `1m` и сообщает `dataThrough`.

Результат: aggregate schema и query strategy.

## G14. Формулы показателей

Статус: `DECIDED`, блок согласован.

- [x] Заменить неоднозначный calendar time на `coveredTime`; отдельно определить planned production, operating и productive time.
- [x] Определить RUN, IDLE, DOWN, planned stop, setup и offline durations без double count.
- [x] Использовать `availability=(RUN+IDLE)/(RUN+IDLE+DOWN+SETUP)`.
- [x] Определить `output` и `scrap` через delta накопительных счётчиков с согласованным reset.
- [x] Использовать `performance=output/(nominalRatePerHour×operatingHours)`; unit задаётся `productionUnit`.
- [x] Разделить `stopCount`, `failureCount` и `recoveryCount`.
- [x] Использовать простые MVP-формулы `MTBF=operatingTime/failureCount`, `MTTR=downTime/failureCount`.
- [x] Агрегировать machine → line → enterprise через суммы совместимых numerators и denominators.
- [x] Определить равный previous period и previous occurrence той же Shift.
- [x] Проверить Availability, Performance, Quality, OEE, MTBF, MTTR и scope aggregation числовыми примерами.

Результат: metrics catalog с формулами, примерами и null semantics.

## G15. Timeseries, Pareto и Chronometry

Статус: `DECIDED`, блок согласован.

- [x] Использовать `AUTO|5m|15m|1h|1d`; fixed buckets выравнивать по UTC, день — по локальной дате Enterprise.
- [x] Использовать `shiftId` как фильтр и `shiftId+shiftDate` для occurrence; не считать смену размером bucket.
- [x] Ограничить numeric telemetry series 720 points с автоматическим укрупнением целых минут без interpolation/raw scan.
- [x] Возвращать MIN/MAX/AVG/FIRST/LAST для GAUGE и FIRST/LAST/DELTA/reset count для COUNTER.
- [x] Определить Pareto share, cumulative share, `UNCLASSIFIED`, `OTHER`, top default 5/max 20.
- [x] Возвращать точный Chronometry одной Machine за occurrence смены; top reasons читать отдельным Pareto.
- [x] Унифицировать requested/actual boundaries, `dataThrough`, `partial`, gaps, zero и null semantics.

Результат: query semantics для аналитических экранов.

---

# H. Инциденты и причины потерь

## P14. ManualIncident

Статус: `DECIDED`, блок согласован.

Уже принято: в MVP поддерживаются только ручные инциденты.

- [x] Определить единый ManualIncident для state override, reason annotation или обоих эффектов.
- [x] Разрешить `to=null` как ongoing manual state override и отдельный close command.
- [x] Назначать причину только effective IDLE/DOWN/SETUP/PLANNED_STOP, игнорировать RUN/OFFLINE.
- [x] Проверять state-effect и reason-effect overlaps независимо; разрешить пересечение state-only и reason-only.
- [x] Определить create/get/list/update/close и idempotent soft cancel без restore.
- [x] Сохранять timestamps/cancelledAt без полного version audit в MVP.
- [x] Использовать необязательный непроверенный `author`; JWT не подтверждает это display-поле.
- [x] Создавать minute-aligned dirty window по union прежних/новых boundaries без replay raw/calculated state.

Результат: incident lifecycle и validation rules.

## P15. LossReason

Статус: `DECIDED`, блок согласован.

- [x] Определить id/enterpriseId/code/name/description/category/color/status/timestamps и уникальность code/name.
- [x] Использовать enterprise scope.
- [x] Использовать закрытый `LossCategory` enum; не хранить `isPlanned`, выводить его из state.
- [x] Использовать optional color формата `#RRGGBB`.
- [x] Использовать ACTIVE/DISABLED; disabled блокирует новые назначения, но сохраняет историю и ongoing incidents.
- [x] Не создавать unknown-row: `lossReasonId=null` означает `UNCLASSIFIED`, `OTHER` является synthetic analytics category.

Результат: loss reason catalog model.

## H16. Наложение причин на интервалы

Статус: `DECIDED`, блок согласован.

- [x] Строить effective projection по union calculated/incident boundaries.
- [x] Manual `SETUP/PLANNED_STOP` перекрывает business state, сохраняя underlying calculated state для data quality.
- [x] Применять reason к IDLE/DOWN/SETUP/PLANNED_STOP, игнорировать portions RUN/OFFLINE.
- [x] Запретить отдельные state/reason overlaps; разрешить независимое пересечение state-only и reason-only.
- [x] После mutation асинхронно пересчитывать effective intervals, state/loss buckets и shift metrics.

Результат: deterministic loss attribution algorithm.

---

# I. Генератор

## P16. Generator domain и режимы запуска

Статус: `DECIDED`, домен и execution semantics согласованы; требуется перенос в OpenAPI.

Уже принято: generator отдельный; поддерживает REALTIME, HISTORICAL и SCHEDULED; пишет сырые сигналы.

- [x] Определить Scenario, Run, RunStatus и Snapshot; отдельную recurring Schedule не вводить.
- [x] Определить ordered phases и `ONCE|LOOP`.
- [x] Определить deterministic run seed и стабильные per-behavior sub-seeds.
- [x] Определить базовый каталог per-signal behavior models; физическую component correlation оставить I17.
- [x] Определить realtime wall clock и historical virtual clock без realtime catch-up.
- [x] Ограничить historical `[from,to)` 90 сутками и скоростью 1000–2000 measurements/s с throttling.
- [x] Scheduled принимает timestamp с offset, хранит UTC, не пишет future raw и использует misfire threshold 30 секунд.
- [x] Определить start/status/stop/failure, progress/checkpoint, retry и HTTP-idempotency.
- [x] При старте сохранять самостоятельный снимок текущей machine configuration.
- [x] Активный run продолжает работу по снимку; новый run с `DISABLED`-сущностью не запускается.
- [x] Определить bounded buffer, ограниченный retry и приоритет realtime над historical.
- [x] Определить `TelemetrySink.writeBatch` и JDBC writer protocol.

Результат: `docs/bmad/specs/spec-generator-domain/` и `docs/bmad/specs/spec-generator-run-execution/`.

## I17. Физически согласованные модели поведения

Статус: `DECIDED`, сложная физическая корреляция сигналов отложена за MVP.

- [x] Использовать диагностические `expectedState`: RUN, IDLE, DOWN, SETUP, PLANNED_STOP, OFFLINE; официальный state выводит только Analytics.
- [x] Для MVP достаточно независимых per-signal behaviors; каталог numeric/counter/boolean/string и фаз уже задан.
- [x] Межсигнальная физическая корреляция, inertia и компонентные модели исключены; не симулировать физическую точность.
- [x] Ramp, noise, missing measurements и quality flags поддерживаются отдельными моделями/параметрами существующего каталога.
- [x] `expectedState` хранится в Phase только как диагностическая подсказка для golden tests.
- [x] Эталонные end-to-end fixtures обязательны в M02; сами fixtures создаются вместе с implementation stories.

Результат: behavior model catalog и golden datasets.

---

# J. Пользовательские потоки

## P17. Создание и настройка структуры

Статус: `DECIDED`, блок согласован.

- [x] Описать создание Enterprise и Shift.
- [x] Описать создание и reorder Lines.
- [x] Описать создание Machine как DISABLED.
- [x] Описать построение Component tree.
- [x] Описать добавление Signals.
- [x] Описать настройку StateRules.
- [x] Описать полную validation и активацию Machine.
- [x] Описать update и disable flows.
- [x] Для каждого шага определить ошибки и recovery.

Результат: user journeys конфигуратора.

## J18. Операционный мониторинг

Статус: `DECIDED`, API-flow согласован.

- [x] Описать выбор предприятия/линии/машины.
- [x] Описать current states overview.
- [x] Описать machine detail и latest signals.
- [x] Описать freshness и stale UI states.
- [x] Использовать polling только current endpoints; historical reads обновляются по context или после mutations.
- [x] Разделить пустой `200`, `404`, projection lag и transport failure.

Результат: user journey оператора и требования к read API.

## J19. Историческая аналитика

Статус: `DECIDED`, API-flow согласован.

- [x] Описать выбор scope, period и shift.
- [x] Описать summary и comparison.
- [x] Описать telemetry series.
- [x] Описать loss timeseries и Pareto.
- [x] Описать chronometry.
- [x] Описать ручную классификацию потери из timeline.
- [x] Описать recalculating/stale/partial data states.

Результат: user journey аналитика и требования к query API.

## J20. Управление генерацией

Статус: `DECIDED`, Scenario и run-mode flows согласованы; требуется перенос в OpenAPI.

- [x] Описать создание disabled Scenario, validation и activation.
- [x] Описать realtime run с bounded/unbounded execution и skipped overdue ticks.
- [x] Описать historical generation, chunk/checkpoint и overlap protection.
- [x] Описать future scheduled run, readiness revalidation, cancel и misfire.
- [x] Описать common progress, idempotent stop, retryable failure и retry.
- [x] Описать переход по analytics context и отдельную проверку `dataThrough/stale/recalculating`.

Результат: user journey пользователя generator.

---

# K. API и контракт с Web

## P20. Analytics OpenAPI

Статус: `DECIDED`, контракт сформирован и провалидирован.

- [x] Составить use-case-oriented список operations после фиксации домена.
- [x] Определить create/update DTO отдельно от response DTO.
- [x] Определить filters, sorting, pagination и status selection.
- [x] Определить response envelopes и analytics metadata.
- [x] Определить Error DTO, field errors, business codes и traceId.
- [x] Определить HTTP status codes и idempotency операций.
- [x] Определить generated client/server boundaries.
- [x] Определить nullable/optional semantics OpenAPI 3.1.
- [x] Подготовить contract examples для основных flows.

Результат: Analytics API v1.0.0 в `fkit-bi-analytics/docs/contracts/analytics-api-draft.yaml` и spec-пакет `spec-analytics-api-contract`.

## P21. Трассировка текущего draft API

Статус: `DECIDED`, выполнено.

Уже принято: `draft-api.yaml` — пример, а не ограничение доменной модели.

- [x] Для каждой операции draft определить сохраняемый пользовательский use case.
- [x] Отметить операции: keep/change/split/remove.
- [x] Сопоставить старые и новые DTO.
- [x] Проверить, что итоговый API не потерял необходимый экран или показатель.
- [x] Подготовить frontend migration notes.

Результат: traceability matrix draft → final API.

## K22. Generator OpenAPI

Статус: `DECIDED`, контракт сформирован и Redocly lint пройден без warnings.

- [x] Определить шесть operations Scenario без physical DELETE.
- [x] Определить validation несохранённого Scenario и validation result сохранённого resource.
- [x] Определить discriminated create для realtime/historical/scheduled Run и required `Idempotency-Key`.
- [x] Определить cursor journal, detail, progress, counters и analytics context.
- [x] Определить idempotent stop/cancel и guarded retry.
- [x] Определить common ErrorResponse и stable validation/conflict codes.
- [x] Подготовить request/response DTO, polymorphic behaviors и examples.

Результат: Generator API v1.0.0 в `fkit-bi-generator/docs/contracts/generator-api-draft.yaml` и `docs/bmad/specs/spec-generator-api-contract/`; 12 operations, все `$ref` разрешены.

---

# L. Надёжность, безопасность и эксплуатация

## L01. Транзакции и идемпотентность

Статус: `DECIDED`, транзакционные границы, Spring JDBC и восстановление фоновых публикаций согласованы.

- [x] Определить транзакцию изменения полной machine configuration.
- [x] Определить короткую атомарную telemetry batch transaction и packet-level idempotency.
- [x] Определить calculation window publication transaction.
- [x] Определить incident update и loss recalculation.
- [x] Определить idempotency всех фоновых шагов.
- [x] Определить recovery после частичного сбоя.
- [x] `POST ManualIncident` требует `Idempotency-Key`; повтор с тем же key/body возвращает исходный incident, другое тело под тем же key — `409`.

Результат: `docs/bmad/specs/spec-transaction-idempotency/`.

## L02. Конкурентность

Статус: `DECIDED`, политика быстрой координации и принятые риски согласованы.

- [x] Определить конкурентное редактирование конфигурации без configuration versions; last-committed-write-wins принят осознанно.
- [x] Определить блокировки machine calculation.
- [x] Определить конкурентные generator runs одной машины и общий historical slot.
- [x] Определить координацию нескольких application instances через PostgreSQL.
- [x] Определить stable lock ordering, быстрый отказ при contention и bounded retry для безопасной фоновой работы.

Результат: `docs/bmad/specs/spec-concurrency/`.

## L03. Безопасность и аудит MVP

Статус: `DECIDED`, auth и deployment security contract зафиксированы; runtime implementation/testing остаются планом реализации.

- [x] Обязательный JWT Bearer для Analytics и Generator API; одинаковые права без ролей/RBAC.
- [x] `author` остаётся непроверенным display value; полный audit configuration/incidents вне MVP.
- [x] Сохранить отдельные least-privilege DB users, секреты вне репозитория, лимиты и safeguards из утверждённых блоков.
- [x] Nginx поддерживает HTTPS на `*.bi.kitexp.ru`, Certbot public wildcard и self-signed demo/dev режимы.
- [x] Первая базовая учётная запись provisioned оператором; только она добавляет пользователей через минимальную форму, без ролей/RBAC.
- [x] DNS управляется Yandex Cloud DNS; wildcard challenge планируется автоматизировать Certbot `dns-yandexcloud` с минимально привилегированной service account.
- [x] Публиковать Nginx на host ports 80/443; внутренние порты приложений и БД не публиковать.
- [x] Основной host — `bi.kitexp.ru`; сертификат включает `bi.kitexp.ru` и `*.bi.kitexp.ru`.
- [x] Зафиксировать issuer/claims/алгоритм/срок JWT, token storage, bootstrap и минимальные поля формы пользователя.
- [x] Зафиксировать DNS plugin credentials как deploy-time secret с минимальными правами.
- [x] Описать отдельный Auth OpenAPI: login, bootstrap-only создание пользователя, ошибки и abuse limits.

Результат: `docs/bmad/specs/spec-security-audit/` и `docs/contracts/auth-api.yaml` (2 operations).

## L04. Наблюдаемость

Статус: `DECIDED`, metrics/runtime часть согласована; structured logs остаются отдельной детализацией реализации.

- [x] Включить Prometheus, Grafana, postgres_exporter и node_exporter в стандартный Compose startup.
- [x] Определить health/readiness и независимость business services от observability.
- [x] Определить metrics: ingestion/generation, processing lag, dirty backlog, jobs, failures, API, PostgreSQL и host.
- [ ] Детализировать structured logs и correlation IDs при проектировании реализации.
- [x] Определить alerts для target health, dropped telemetry, lag, backlog, API, connection и disk pressure.
- [x] Определить operational endpoints ручного перерасчёта в analytics API contract; execution metrics входят в observability.

Результат: `docs/bmad/specs/spec-observability-runtime/`.

## L05. Миграции и начальные данные

Статус: `DECIDED`.

- [x] Определить порядок Liquibase migrations.
- [x] Liquibase загружает согласованные `signal_semantic` и `measurement_unit`; закрытые ComponentKind/state/quality значения хранятся по SQL/API validation rules, без PostgreSQL native enum.
- [x] Не создавать tenant-specific LossReason до Enterprise; новый Enterprise начинает с пустого справочника, причины пользователь добавляет обычным API flow.
- [x] Raw partition maintenance заранее держит активное 90-дневное окно плюс 7 дней вперёд; DDL не выполняется в ingestion transaction.
- [x] Не мигрировать sample OpenAPI/UI draft данные. Существующая dev DB несёт только Flyway marker и не очищается; MVP доменные данные создаются заново.
- [x] Определить rollback/forward-only policy.

Результат: `spec-sql-equipment-foundation/liquibase-conventions.md` и `spec-raw-telemetry-ingestion/telemetry-storage.md`.

---

# M. Проверка и подготовка реализации

## M01. Acceptance criteria и примеры

Статус: `OPEN`.

- [ ] Для каждой команды определить Given/When/Then.
- [ ] Для каждой формулы подготовить числовой пример.
- [ ] Для state rules подготовить timeline examples.
- [ ] Для late/history/future подготовить event-time examples.
- [ ] Для status hierarchy подготовить validation examples.

Результат: executable acceptance catalog.

## M02. Стратегия тестирования

Статус: `OPEN`.

- [ ] Unit tests чистых rule/metric calculators.
- [ ] Property tests непересекающихся intervals и сохранения длительности.
- [ ] Integration tests PostgreSQL constraints и migrations.
- [ ] Golden datasets generator → telemetry → intervals → metrics.
- [ ] Contract tests OpenAPI.
- [ ] Load tests realtime и historical backfill.
- [ ] Recovery tests после падения calculation.

Результат: test strategy.

## M03. Финальная согласованность документов

Статус: `OPEN`.

- [ ] Обновить исходные architecture/components documents.
- [ ] Удалить устаревшие противоречия.
- [ ] Синхронизировать SQL, OpenAPI и glossary.
- [ ] Проверить traceability requirements → model → API → tests.
- [ ] Зафиксировать оставшийся technical debt MVP.

Результат: единый непротиворечивый planning package.

## M04. Сборка итоговой спецификации

Статус: `OPEN`.

- [ ] Сформировать подробный документ спецификации из закрытых решений.
- [ ] Провести validation спецификации.
- [ ] Сформировать architecture spine.
- [ ] Разбить работу на epics и stories.
- [ ] Провести implementation readiness check.

Результат: утверждённая спецификация, готовая к планированию реализации.

---

# Рекомендуемый порядок прохождения

1. `A01–A04` — scope, actors, glossary, нагрузка.
2. `P02–P09` и `C10` — доменная модель оборудования.
3. `P03` — статусы после определения всех сущностей.
4. `P10`, `D11`, `D12` — состояния и правила.
5. `P11`, `E12`, `E13` — сырой telemetry contract.
6. `P12`, `P18`, `P19` — расчётный конвейер.
7. `P13`, `G14`, `G15` — агрегаты и формулы.
8. `P14`, `P15`, `H16` — инциденты и потери.
9. `P16`, `I17` — generator domain.
10. `P17`, `J18–J20` — полные пользовательские потоки.
11. `P20`, `P21`, `K22` — OpenAPI и frontend migration.
12. `L01–L05` — надёжность и эксплуатация.
13. `M01–M04` — проверка, финализация и декомпозиция.

# Первая рабочая сессия

Рекомендуемый старт: `A01. Границы MVP и результат демонстрации`.

Причина: без точного MVP мы рискуем одинаково подробно проектировать обязательные функции и будущие возможности. После A01 сразу переходим к `A02` и `A03`, затем фиксируем нагрузочный профиль `A04`, поскольку он влияет на SQL telemetry contract и rollup.
