# FKIT BI — рабочие заметки по проектированию аналитики

Статус: черновик для обсуждения. Документ фиксирует согласованные решения и отделяет их от предложений, которые ещё предстоит утвердить.

## Зафиксированные решения

- В MVP `fkit-bi-analytics` остаётся одним Spring Boot-приложением и одним deployable. REST API, фоновая обработка, расчёт состояний и запросы аналитики разделяются внутренними модулями с явными интерфейсами, чтобы позднее их можно было вынести в отдельные приложения без переделки доменной модели.
- В MVP используется одна PostgreSQL. Сырые данные, конфигурация, производные интервалы, агрегаты, инциденты и данные генератора разделяются логическими схемами и правами доступа, но не физическими базами.
- Сервис генерации остаётся отдельным Spring-приложением; решение об одном сервисе относится к API и расчётному контуру `fkit-bi-analytics`.
- Для конфигурационных сущностей используются только состояния `ACTIVE` и `DISABLED`. Отдельные состояния `DRAFT`, `ARCHIVED` и `SUPERSEDED` не вводятся.
- Собственный `status` хранится у `Enterprise`, `Shift`, `ProductionLine`, `Machine`, `Component` и `TelemetrySignal`. `Sensor` и `Instrument` являются значениями `Component.kind`, а не отдельными сущностями. `effectiveStatus` не вводится, не хранится, не вычисляется и не возвращается API.
- Новая конфигурационная сущность может создаваться в состоянии `DISABLED`. Перевод в `ACTIVE` разрешается только после полной доменной проверки.
- Конфигурационные сущности в MVP не удаляются физически через пользовательский API; вместо удаления используется `DISABLED`, чтобы сохранить связи с телеметрией и аналитической историей.
- Машина всегда принадлежит предприятию и может быть создана без линии. `lineId` допускает один переход из `null` в линию того же предприятия; после назначения перенос или снятие с линии в MVP запрещены.
- Свободные машины можно назначать линии индивидуально или атомарным пакетом. Любой конфликт отменяет весь пакет; машина без линии может конфигурироваться, но не участвует в генерации, приёме производственной телеметрии и аналитике.
- Компоненты любого вида в MVP закрепляются за машиной и не переносятся между машинами.
- Для основных конфигурационных сущностей используется стабильный технический код, отдельный от внутреннего UUID. `Enterprise` и `LossReason` имеют глобально уникальный код; `Shift` и `ProductionLine` — уникальный внутри предприятия; `Machine` — уникальный внутри предприятия; `Component` и `TelemetrySignal` — уникальный внутри машины.
- Технический код предлагает frontend; backend проверяет формат и уникальность, сохраняет его и запрещает изменение, но сам не выполняет транслитерацию или генерацию.
- Enterprise поддерживает обязательный IANA timezone; его изменение блокируется после появления телеметрии, инцидентов, запусков генератора или рассчитанной аналитики. Смены являются отдельными сущностями.
- ProductionLine сортируется по изменяемому `sortOrder` и затем стабильному `code`; при отсутствии значения backend назначает шаг `10` после текущего максимума.
- Machine создаётся в `DISABLED`; `machineType` является свободной необязательной строкой, `inventoryNo` необязателен и уникален внутри Enterprise, а `nominalRate` задаётся положительной парой с `productionUnit`.
- В MVP конфигурация машины не версионируется. Хранится только текущая конфигурация; её изменение полностью валидируется и сохраняется одной транзакцией.
- Генератор при запуске сохраняет самостоятельный снимок текущей конфигурации без ссылки на номер версии. Последующие изменения машины не влияют на уже запущенный сценарий.
- Отключение участвующей конфигурационной сущности не останавливает и не отменяет активный generator run: он продолжает работу по сохранённому снимку. Новый run с необходимой сущностью в `DISABLED` не запускается; точная ошибка и `RunStatus` определяются контрактом генератора.
- Ограничение MVP: повторный расчёт старой телеметрии после изменения правил использует текущую конфигурацию и текущие правила.
- В системе используются предприятия, производственные линии, станки и дерево вложенных компонентов. Датчики, приборы, инструменты, механизмы и обеспечивающие системы моделируются значениями `Component.kind`.
- `TelemetrySignal` всегда принадлежит машине и при необходимости ссылается на компонент той же машины; отсутствие ссылки означает сигнал уровня машины.
- `TelemetrySignal` описывает конфигурацию канала, а `TelemetryMeasurement` — отдельный неизменяемый raw-факт. Типы значения MVP: `DOUBLE`, `LONG`, `BOOLEAN`, `STRING`; виды последовательности: `GAUGE`, `COUNTER`, `STATE`.
- `semanticCode` и `unitCode` являются стабильными расширяемыми кодами; протокольный `sourceAddress` не входит в домен сигнала, а роль в состоянии задаётся ссылкой из `StateRule`, не флагом на сигнале.
- `expectedIntervalMs` и `staleAfterMs` необязательны; фактическая частота генерации задаётся сценарием generator. Raw вне `validMin/validMax` сохраняется с качеством, а не отбрасывается.
- Идентичность и смысловые поля сигнала блокируются после первого raw; изменение физического смысла создаёт новый сигнал. Высокочастотные waveform и частота выше 1 Hz не входят в MVP.
- Родителя компонента можно изменить только внутри той же машины при атомарной проверке отсутствия циклов. Исторические данные отображаются через текущую структуру, поскольку её версии в MVP не хранятся.
- Генератор создаёт сырые показания сигналов компонентов. Официальные состояния машины и показатели рассчитывает сервис аналитики.
- Операционное состояние машины принимает `RUN`, `IDLE`, `DOWN`, `PLANNED_STOP`, `SETUP` или `OFFLINE`; оно не хранится в строке `Machine` и raw telemetry, а сохраняется аналитикой как текущая проекция и временные интервалы.
- State classification: `RUN` productive/operating; `IDLE` operating performance loss; `DOWN` unplanned availability loss; `SETUP` planned operational availability loss; `PLANNED_STOP` excluded time; `OFFLINE` data gap, не downtime.
- Базовые additive facts: `plannedProductionTime=RUN+IDLE+DOWN+SETUP`, `operatingTime=RUN+IDLE`, `productiveTime=RUN`; Availability вычисляется из сумм, а IDLE влияет на последующий Performance.
- Data coverage использует underlying calculated OFFLINE даже под manual override; percentages и ratios разных buckets/machines не усредняются.
- `coverageFrom` state timeline фиксируется при первой активации Machine. Published history имеет UTC-minute-aligned полуоткрытый coverage `[coverageFrom,dataThrough)`, но точные transitions сохраняют миллисекундный event time.
- `machine_state_interval` делится только при изменении MachineState; historical matched rule/quality не хранятся. Current projection отдельно возвращает matched rule, evaluation quality, `stateSince`, currency и `recalculating`.
- Dirty windows нормализуются по UTC-минутам, объединяются на Machine, расширяются до левого evaluator context и пересчитываются до current `dataThrough`.
- Долгий replay пишет validated staging; active range, current projection и checkpoints подменяются короткой транзакцией, пока frontend читает старый committed результат.
- Ближайшие stale/delay/offline transitions хранятся одной строкой `machine_evaluation_deadline` на Machine и выполняются PostgreSQL worker с lease/`SKIP LOCKED`, без внешнего broker.
- Пользовательский state recalculation асинхронно принимает `PERIOD` или `ALL`; изменение rules пересчитывает current, а исторический период выбирает пользователь и он использует текущие rules.
- Analytics HTTP API зафиксирован отдельным OpenAPI 3.1 в `fkit-bi-analytics/docs/contracts/analytics-api-draft.yaml`; SQL-контракт телеметрии и OpenAPI генератора проектируются отдельно.
- `fkit-bi-analytics/docs/contracts/draft-api.yaml` используется как пример пользовательских сценариев и требуемых представлений данных, но не ограничивает проектируемую доменную модель. Пути, операции и DTO могут быть изменены, добавлены или удалены; итоговый OpenAPI формируется после согласования домена и расчётов, а Web-клиент адаптируется к нему.
- Правила определения состояний должны быть декларативными.
- Для каждой Machine хранится одна текущая `MachineStateConfig` без версий: `defaultState`, `offlineAfterMs` и до 20 StateRule в валидированном JSONB; PUT заменяет её атомарно, runtime использует скомпилированную типизированную модель.
- StateRule имеет unique priority, target state, enter/optional exit conditions и activation/release delays. Hysteresis выражается разными enter/exit thresholds; `OFFLINE` зарезервирован системой.
- AST ограничен `ALL`, `ANY`, `NOT`, `COMPARE`; operators: `EQ`, `NE`, `GT`, `GTE`, `LT`, `LTE`, `BETWEEN`, `IN`. Для `DOUBLE EQ/NE` обязателен tolerance; signal-to-signal, арифметика, regex, scripts и windows не входят в MVP.
- Evaluator использует TRUE/FALSE/UNKNOWN, выбирает rule по priority, возвращает default state при отсутствии active rule и сообщает `evaluationQuality=COMPLETE|DEGRADED`. Переход различает `effectiveFrom` и `detectedAt`.
- В MVP расчёты выполняются непрерывно планировщиком; HTTP API синхронно читает подготовленные результаты.
- Ingestion принимает пакеты измерений и не рассчитывает аналитику в транзакции записи. Общие фоновые workers обновляют последние значения, состояния и rollup; отдельная задача на каждый сигнал не создаётся.
- Frontend не строит аналитику из raw и не выбирает физический источник: он читает предметные текущие проекции, интервалы, временные ряды нужной гранулярности и сменные итоги с признаком актуальности.
- Смены определяются предприятием. API использует реальный UUID `shiftId`; пользовательские коды могут называться `day` и `night`, но системной семантики и литералов `all/day/night` нет.
- Shift ежедневно повторяется в IANA timezone предприятия в пределах `[validFrom, validTo)`. Конкретная occurrence вычисляется по event time и идентифицируется парой `shiftId + shiftDate`; отдельные ежедневные строки не создаются.
- Использованные границы Shift не изменяются: старое определение закрывается через `validTo`, а новое расписание получает новый `id` и `code`. Пересечения запрещены, промежутки разрешены и дают `shiftId = null`.
- `DISABLED` Shift исключается из новых operational-настроек и generator runs, но сохраняет историческое чтение и перерасчёт в validity-интервале.
- Ответы аналитики должны содержать сведения об актуальности данных и расчёта.
- `signal_current_value` отдельно хранит last received и last usable measurement. Только `GOOD` без disqualifying flags является usable; `UNCERTAIN`, `BAD` и out-of-range остаются видимыми, но не заменяют расчётное значение.
- Freshness сигнала вычисляется как `NO_DATA`, `FRESH` или `STALE` по `lastUsableObservedAt`, `staleAfterMs` и event-time reference; это не lifecycle status и не `effectiveStatus`.
- Каждый сигнал, используемый StateRule, обязан иметь `staleAfterMs`; после устаревания вход правила становится `UNKNOWN`.
- Системный `OFFLINE` проверяется до пользовательских правил по отсутствию любой принятой telemetry машины дольше `offlineAfterMs`; default MVP — 60 секунд.
- Генератор фиксирует снимок текущей конфигурации для запуска; история версий конфигурации оборудования в MVP не ведётся.
- В MVP поддерживаются только ручные инциденты.
- ManualIncident может вручную задавать past/current `[from,to)` override `SETUP` или `PLANNED_STOP`; overlapping overrides одной Machine запрещены, `to=null` означает ongoing.
- Ручной override не редактирует raw или calculated state timeline. Асинхронная effective projection применяет manual state для business analytics, но сохраняет underlying calculated state, включая `OFFLINE`, для data-quality metrics.
- Incident mutation создаёт minute-aligned dirty window и пересчитывает effective intervals, shift/state/loss buckets; повторный StateRule replay не теряет manual classification.
- Генератор должен поддерживать генерацию в реальном времени, историческую генерацию и запланированные будущие запуски по заданным условиям и времени.
- Минимальный demo host: 4 vCPU, 8 GB RAM и SSD 100 GB; рекомендуется 150 GB. Nominal profile — 20 машин по 15 активных сигналов со средним периодом 10 секунд; sustained benchmark — 200 measurements/s, burst — 1000/s на 60 секунд.
- Raw telemetry хранится 90 суток в суточных UTC partitions. Удаление выполняется целыми partitions после закрытия dirty windows и публикации производных данных; после удаления полный перерасчёт диапазона невозможен.
- Current API p95 должен укладываться в 500 ms, overview — 1 s, аналитика до 30 суток — 2 s и до 90 суток — 5 s. Current signal/state/rollup lag ограничен 15/20/120 секундами при nominal profile.
- Prometheus, Grafana, postgres_exporter и node_exporter обязательны и запускаются стандартным `docker compose up -d`. Они не являются readiness-зависимостью business services.
- Prometheus собирает Micrometer application metrics, PostgreSQL и host metrics каждые 15 секунд, хранит их 7 суток в пределах 1 GB. Grafana datasource, шесть dashboard и alert rules provisioned из `fkit-bi-infra`.
- Metric labels не содержат `enterpriseId`, `lineId`, `machineId`, `signalId`, `batchId`, `runId` или `incidentId`; предметная детализация остаётся в API и structured logs.
- Generator использует уже созданные через Analytics API Enterprise, ProductionLine, Machine, Component и TelemetrySignal; собственного equipment CRUD у него нет.
- `GenerationScenario` принадлежит Enterprise, может включать несколько его машин, имеет stable code и `ACTIVE|DISABLED`. Неполный Scenario сохраняется disabled, а activation/run требуют полной readiness validation.
- Scenario содержит ordered phases, `ONCE|LOOP` и типизированные per-signal behavior models. `expectedState` является только диагностической подсказкой и никогда не записывается как официальный MachineState.
- Scenario versions не ведутся. Каждый GenerationRun сохраняет immutable snapshot Scenario/equipment/signals и deterministic random seed в PostgreSQL.
- Одноразовый будущий запуск представлен `SCHEDULED` Run; отдельная recurring Schedule entity вне MVP. Run использует statuses `SCHEDULED|QUEUED|RUNNING|STOP_REQUESTED|COMPLETED|STOPPED|CANCELLED|FAILED`.
- Одна Machine не участвует в двух realtime executions, future reservations не пересекаются, multi-machine start атомарен; на минимальном стенде выполняется один historical Run.
- Realtime Run использует wall clock и пропускает overdue ticks без catch-up burst. Historical Run использует virtual clock, диапазон до 90 суток, пятиминутные chunks и deterministic batch IDs. Scheduled Run хранит UTC start и завершается `SCHEDULE_MISSED` при опоздании больше 30 секунд.
- Run progress основан на event-time coverage; unbounded realtime не имеет процента. Stop ограниченно завершает текущую запись/flush, retry разрешён только для retryable failure и сохраняет runId/snapshot/seed с новым attempt.
- `POST /runs` требует `Idempotency-Key`. `COMPLETED` подтверждает окончание raw generation, а frontend отдельно проверяет готовность Analytics по `dataThrough`, `stale` и `recalculating`.
- Scenario payload оптимизирован одним уровнем inheritance: Machine target хранит optional base behaviors, phase — только `REPLACE|DISABLE` overrides, а Run snapshot содержит полностью развёрнутую effective behavior matrix.
- Публичный Generator API содержит 12 operations: шесть для Scenario и шесть для Run. Equipment selection остаётся в Analytics API, raw ingestion — во внутреннем `TelemetrySink`.

## Транзакции, persistence и восстановление

- Для Java persistence в MVP выбран Spring JDBC (`JdbcTemplate`/`NamedParameterJdbcTemplate`), параметризованный SQL, JDBC batch для bulk-записей и mapped read models; JPA/Hibernate не вводится. PostgreSQL `COPY` допускается только при подтверждённой benchmark-ом необходимости.
- Application/service methods задают транзакционные границы через Spring `@Transactional`; repositories используют transaction manager и DataSource приложения. Внешние эффекты не считаются атомарными с PostgreSQL.
- Изменение конфигурации и необходимый durable recalculation work сохраняются атомарно. ManualIncident и dirty range также фиксируются одной transaction; effective projection пересчитывается асинхронно.
- Telemetry batch, header/hash, raw rows, signal usage и recalculation hints остаются одной короткой transaction с packet-level idempotency.
- Replay и durable staging выполняются вне publication transaction. Короткий publication commit заменяет полный затронутый диапазон, обновляет projection currency и завершает work/job/checkpoint вместе; readers видят старую или новую версию целиком.
- Фоновые шаги допускают at-least-once retry и выполняют replace/upsert, а не повторное прибавление; staging после crash можно пересобрать из raw и durable work.
- Открытый вопрос для финальной API-сверки: нужен ли `Idempotency-Key` на POST создания ManualIncident при потере ответа клиентом.

## Конкурентность

- Конкурентные обычные updates конфигурации остаются без version/ETag и используют last-committed-write-wins; пользователь принимает риск перезаписи устаревшего полного PUT ради простоты MVP.
- Главный приоритет — не допускать длительного ожидания на write path и не задерживать read API. Для integrity используют короткие точечные locks/conditional updates; lock contention завершает пользовательскую команду без частичной записи.
- Уже согласованные owner locks, Signal advisory locks, per-machine calculation leases и `SKIP LOCKED` queue сохраняются. `SKIP LOCKED` применяется только для worker queue, не для обычного чтения.
- Generator координирует multiple instances durable machine reservations и одним общим historical capacity slot в PostgreSQL; multi-machine reservation атомарен, reservation locks берутся в стабильном порядке.
- Lease/heartbeat одного `RUNNING` Run удерживает одного executor. При expiry Run становится `FAILED retryable`; автоматического failover нет, explicit retry использует checkpoint. Reservations удерживаются до terminal/recovery transition.
- Несколько resource locks берутся в устойчивом порядке и сортированном UUID порядке; contention для пользовательских операций fail-fast/short-timeout, bounded retry разрешён только безопасной idempotent background work. Числовые timeout/retry limits подтверждаются benchmark-ом.

## Следствия для аналитики

- Обработка выполняется по времени события (`observedAt`), а не только по времени записи в PostgreSQL.
- Запоздавшие и исторические измерения должны помечать ограниченный диапазон времени для повторного расчёта.
- Запланированный будущий запуск начинает публиковать измерения при наступлении времени запуска; заранее записанные будущие измерения не должны изменять текущее состояние.
- Сырая телеметрия является неизменяемым источником повторного расчёта, но пользовательские API не должны выполнять по ней тяжёлые агрегирующие запросы.
- Для raw telemetry приоритетом является доступность сервиса, затем полнота данных и затем немедленная согласованность. Realtime использует bounded buffer и ограниченный retry; при перегрузке допустим наблюдаемый drop пакетов. Это правило не распространяется на конфигурацию, правила, инциденты и generator definitions.
- Raw хранится как batch header и типизированные append-only measurement rows. Идемпотентность действует по `(producerId, producerBatchId)`; per-measurement UUID, FK на Signal, JSONB payload и value indexes на горячем пути не используются.
- Query API, ingestion и calculation workers имеют раздельные connection budgets. Frontend не ждёт расчёт и при lag получает последнюю committed projection с `dataThrough`, `calculatedAt` и `stale`.
- Метрики, пригодные для суммирования, хранятся как числители и знаменатели. Проценты и коэффициенты вычисляются в API; готовые проценты не усредняются.
- `plannedProductionTime=RUN+IDLE+DOWN+SETUP`, `operatingTime=RUN+IDLE`, `productiveTime=RUN`; Availability равна `operatingTime/plannedProductionTime`.
- `PRODUCTION_COUNT` включает все завершённые изделия, `SCRAP_COUNT` — брак; Performance использует nominal output за `RUN+IDLE`, Quality равна `(output-scrap)/output`, OEE — произведению Availability, Performance и Quality.
- `stopCount` считает `RUN→IDLE/DOWN`, `failureCount` — входы в DOWN, `recoveryCount` — выходы из DOWN; для demo MVP `MTBF=operatingTime/failureCount`, `MTTR=downTime/failureCount`.
- Line/Enterprise сначала суммируют совместимые machine numerators и denominators. Производственные показатели для несовместимых `productionUnit` равны `null`; time metrics остаются доступны.

## Предлагаемый вычислительный конвейер

1. Генератор или будущий источник атомарно записывает пакет исходных измерений.
2. Обнаружитель новых пакетов читает их по монотонному идентификатору приёма и создаёт или объединяет диапазоны повторного расчёта по времени события.
3. Проектор телеметрии обновляет последние значения сигналов и временные rollup-таблицы.
4. Проектор состояний восстанавливает снимки сигналов, применяет правила и идемпотентно заменяет затронутые интервалы состояний.
5. Проектор метрик пересчитывает бакеты состояний, выпуска и переходов.
6. Проектор потерь объединяет интервалы состояний с ручными причинами.
7. API читает текущие проекции, интервалы и подходящий уровень агрегатов.

## Предлагаемые производные данные

- `signal_current_value` — последнее достоверное и последнее полученное значение каждого сигнала.
- `machine_current_state` — текущее вычисленное состояние каждой машины.
- `machine_state_interval` — точная история непересекающихся интервалов состояний.
- `signal_numeric_rollup_1m` — качество, минимум, максимум, сумма, количество, первое и последнее usable-значения; для COUNTER также delta и reset count.
- `machine_metric_bucket_1m` — длительности состояний, выпуск, брак и счётчики переходов.
- `machine_loss_bucket_1m` — длительности потерь по ручным причинам и без указанной причины.
- `analytics_dirty_window` — очередь диапазонов, которые требуется пересчитать из-за новых, запоздавших или исторических данных.
- `analytics_checkpoint` — техническое состояние обнаружения и выполнения расчётов.

Для demo MVP физически сохраняются три минутные проекции: `signal_numeric_rollup_1m`, `machine_metric_bucket_1m` и `machine_loss_bucket_1m`. Третья нужна для функционального и быстрого Pareto по причинам без query-time соединения точных intervals. STATE/BOOLEAN не получают универсальную интервальную проекцию, а `5m/15m/1h/1d` таблицы не создаются.

## Предлагаемые внутренние модули `fkit-bi-analytics`

- `equipment` — предприятия, смены, линии, машины, компоненты, сигналы и их текущая конфигурация.
- `telemetry` — SQL-контракт исходных измерений, чтение пакетов, актуальность и последние значения.
- `calculation` — очередь диапазонов пересчёта, декларативные правила, состояния и интервалы.
- `aggregation` — минутные rollup, выпуск, переходы и потери; более крупные response buckets собираются при чтении.
- `incident` — справочник причин и ручные инциденты.
- `analytics-query` — сценарии чтения для dashboard и исторической аналитики.
- `api` — HTTP-контроллеры и транспортные модели; бизнес-логика в контроллерах не размещается.

Модули не обращаются напрямую к внутренним таблицам друг друга. Взаимодействие выполняется через application-интерфейсы и явно выделенные read-модели. Это правило является подготовкой к возможному будущему разделению приложений.

## Согласованные Analytics flows

1. Создание предприятия и графика смен.
2. Создание производственных линий и управление их порядком.
3. Создание машины и её полной текущей конфигурации.
4. Создание дерева компонентов разных видов и привязка сигналов.
5. Настройка и проверка декларативных правил состояний.
6. Получение исходной телеметрии и расчёт текущего состояния.
7. Построение интервалов, агрегатов и ручная классификация потерь.
8. Выдача текущих и исторических данных Web-клиенту.
Analytics API покрывает пункты 1–8 отдельными configuration, operations, analytics, incident и recalculation operations. Пункт 9 относится к отдельному Generator OpenAPI и остаётся следующим самостоятельным блоком.

## Базовые правила агрегирования

- Хранятся длительности состояний, выпуск и количества событий, а не готовые `availability`, `performance`, `MTBF` или `MTTR`.
- `availability`, `performance`, `MTBF` и `MTTR` вычисляются из сумм за выбранный период.
- Исторические ответы demo MVP выравниваются по закрытым UTC-минутам и возвращают фактические границы; raw не читается для достройки неполных краёв запроса.
- Для области предприятия или линии минутные агрегаты машин суммируются по текущей структуре. Перенос Machine между линиями в MVP запрещён.
- `dataThrough` результата должен показывать, до какого времени исходные данные полностью обработаны.
- Late и historical data полностью пересчитывают затронутые минуты и атомарно заменяют их через staging; накопительное обновление `+=` не используется.
- Исторические ряды используют `AUTO|5m|15m|1h|1d`, собирая крупные response buckets из минутных данных. Metric/loss series ограничены 1000 points, telemetry — 720 points, общий период MVP — 90 дней.
- Loss denominator включает IDLE, DOWN и SETUP; PLANNED_STOP показывается отдельно, OFFLINE остаётся data gap. Причина `null` отображается как `UNCLASSIFIED`, остаток Pareto top — как `OTHER`.
- Chronometry строится для `machineId+shiftDate` и optional `shiftId` из точных effective intervals; без `shiftId` возвращаются все occurrences этой локальной даты. Ответ не дублирует группировку тех же intervals по причинам.
- LossReason принадлежит Enterprise, имеет stable code, name, optional description/color, `LossCategory` и ACTIVE/DISABLED. `LossCategory` — закрытый Java/OpenAPI enum, хранимый VARCHAR; сами пользовательские LossReason остаются строками таблицы.
- Единый ManualIncident может содержать SETUP/PLANNED_STOP override, lossReasonId либо оба эффекта. State-effect и reason-effect overlaps запрещаются независимо, state-only и reason-only incidents могут пересекаться.
- Reason применяется к effective IDLE/DOWN/SETUP/PLANNED_STOP и игнорирует RUN/OFFLINE. Ongoing reason продолжает классифицировать новые eligible intervals до close.
- Incident поддерживает update/close/idempotent soft cancel; полный audit, restore, multiple simultaneous causes и automatic reason detection не входят в MVP.

## Открытые решения

- Границы допустимого повторного расчёта после изменения правил и конфигурации; в MVP используются текущие правила.
- Формат structured logs и правила correlation ID при реализации observability.
