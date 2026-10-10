# Физическая модель проекций

## Владение и срок хранения

`telemetry.signal_current_value` — обновляемая Analytics-проекция в schema `telemetry`. Машинное состояние, timeline, минутные bucket’ы, dirty work, jobs, deadlines и staging находятся в schema `analytics`. Raw measurements не обновляются.

Сущности оборудования и инциденты отключаются, а не удаляются. Для проекций используются обычные FK на стабильные владельческие сущности; исключение — raw hot path, где FK отсутствуют по отдельной спецификации ingestion.

Проекции хранятся весь срок demo-данных. Автоматический retention/partitioning для них не вводится. Единственная физическая детализация агрегатов — UTC minute; длительные ряды формируются из минутных фактов.

## Read models

| Таблица | Ключ | Содержимое |
| --- | --- | --- |
| `telemetry.signal_current_value` | `signal_id` | Last received и last usable typed values, их event/receive order и `projected_at` |
| `analytics.machine_current_state` | `machine_id` | `coverage_from`, calculated state, `state_since`, matched rule, evaluation quality, last telemetry time, `data_through`, `calculated_at`, `recalculating` |
| `analytics.machine_state_interval` | `(machine_id, effective_from)` | Calculated state-only timeline с точностью до миллисекунды |
| `analytics.machine_effective_state_interval` | `(machine_id, effective_from)` | Effective/calculated state, источник и ссылки на incident/reason |
| `analytics.signal_numeric_rollup_1m` | `(signal_id, bucket_start)` | Counts качества и числовые GAUGE/COUNTER aggregates |
| `analytics.machine_metric_bucket_1m` | `(machine_id, bucket_start)` | Аддитивные state durations, quantity и transition counts с shift attribution |
| `analytics.machine_loss_bucket_1m` | `(machine_id, bucket_start, state, loss_reason_id)` | Минутная длительность потерь по state/reason; `NULL` означает UNCLASSIFIED |

Typed current values хранятся nullable columns для каждого поддерживаемого типа (`DOUBLE`, `LONG`, `BOOLEAN`, `STRING`) отдельно для last received и last usable. `JSONB` для measurement values не используется. Для каждой группы CHECK требует ровно одно заполненное typed value; у last usable допускается группа из всех `NULL`, если usable measurement ещё не было.

Физические группы `signal_current_value`:

```text
signal_id UUID PK
machine_id UUID NOT NULL
FK (machine_id, signal_id) -> equipment.telemetry_signal(machine_id, id)
last_received_observed_at TIMESTAMPTZ(3) NOT NULL
last_received_at TIMESTAMPTZ(3) NOT NULL
last_received_batch_id BIGINT NOT NULL
last_received_ordinal INTEGER NOT NULL
last_received_double DOUBLE PRECISION NULL
last_received_long BIGINT NULL
last_received_boolean BOOLEAN NULL
last_received_text VARCHAR(500) NULL
source_quality SMALLINT NOT NULL
validation_flags INTEGER NOT NULL
last_usable_observed_at TIMESTAMPTZ(3) NULL
last_usable_received_at TIMESTAMPTZ(3) NULL
last_usable_batch_id BIGINT NULL
last_usable_ordinal INTEGER NULL
last_usable_double DOUBLE PRECISION NULL
last_usable_long BIGINT NULL
last_usable_boolean BOOLEAN NULL
last_usable_text VARCHAR(500) NULL
projected_at TIMESTAMPTZ(3) NOT NULL
```

`(machine_id, signal_id)` — составной FK к Equipment Signal; он сохраняет denormalized owner для машинного current query. `last_received_batch_id` и `last_usable_batch_id` не являются FK: ingest header удаляется по raw retention, а его идентификатор нужен как tie-breaker. Last received всегда имеет ровно одно typed value; last usable либо имеет ровно одно значение и полностью заполненную ordering tuple, либо все значения и tuple пусты. Оба значения обновляются по `(observed_at, ingest_batch_id, ordinal)`. Для current signal DTO поле `calculatedAt` отображает `projected_at`; `dataThrough` при наличии берётся из связанной `machine_current_state`. Машинный current DTO использует собственный `calculated_at` и `data_through`.

Остальные хранимые поля используют следующие базовые типы:

```text
machine_current_state:
  machine_id UUID PK/FK equipment.machine(id)
  coverage_from TIMESTAMPTZ(3) NOT NULL; state VARCHAR(32) NOT NULL
  state_since TIMESTAMPTZ(3) NOT NULL; matched_rule_id UUID NULL
  evaluation_quality VARCHAR(16) NOT NULL
  last_telemetry_observed_at TIMESTAMPTZ(3) NULL
  data_through TIMESTAMPTZ(3) NOT NULL; calculated_at TIMESTAMPTZ(3) NOT NULL
  recalculating BOOLEAN NOT NULL DEFAULT FALSE

machine_state_interval:
  machine_id UUID FK; effective_from TIMESTAMPTZ(3); effective_to TIMESTAMPTZ(3) NULL
  state VARCHAR(32); detected_at TIMESTAMPTZ(3); calculated_at TIMESTAMPTZ(3)

machine_effective_state_interval:
  machine_id UUID FK; effective_from TIMESTAMPTZ(3); effective_to TIMESTAMPTZ(3) NULL
  effective_state VARCHAR(32); calculated_state VARCHAR(32)
  state_source VARCHAR(16); state_incident_id UUID NULL
  loss_reason_id UUID NULL; reason_incident_id UUID NULL
  calculated_at TIMESTAMPTZ(3)

signal_numeric_rollup_1m:
  signal_id UUID FK; bucket_start TIMESTAMPTZ(3)
  sample_count, usable_count, good_count, uncertain_count, bad_count, out_of_range_count INTEGER NOT NULL
  min_value, max_value, sum_value DOUBLE PRECISION NULL
  first_value, last_value DOUBLE PRECISION NULL
  first_observed_at, last_observed_at TIMESTAMPTZ(3) NULL
  delta_value DOUBLE PRECISION NULL; reset_count INTEGER NULL
  calculated_at TIMESTAMPTZ(3)

machine_metric_bucket_1m:
  machine_id UUID FK; bucket_start TIMESTAMPTZ(3)
  shift_id UUID NULL FK equipment.shift(id); shift_date DATE NULL
  covered_duration_ms, run_duration_ms, idle_duration_ms, down_duration_ms BIGINT
  setup_duration_ms, planned_stop_duration_ms BIGINT
  effective_offline_duration_ms, underlying_offline_duration_ms BIGINT
  produced_quantity, scrap_quantity DOUBLE PRECISION NULL
  stop_count, failure_count, recovery_count INTEGER
  calculated_at TIMESTAMPTZ(3)

machine_loss_bucket_1m:
  machine_id UUID FK; bucket_start TIMESTAMPTZ(3)
  shift_id UUID NULL FK equipment.shift(id); shift_date DATE NULL
  state VARCHAR(32); loss_reason_id UUID NULL FK incident.loss_reason(id)
  duration_ms BIGINT CHECK duration_ms > 0; calculated_at TIMESTAMPTZ(3)
```

Закрытые технические значения хранятся как `VARCHAR` с `CHECK`, а расширяемые бизнес-коды — в справочниках с FK. Machine state codes: `RUN`, `IDLE`, `DOWN`, `SETUP`, `PLANNED_STOP`, `OFFLINE`; `state_source`: `CALCULATED`, `MANUAL`. Все event timestamps имеют точность до миллисекунд. Для `signal_numeric_rollup_1m` quality counters неотрицательны и выполняют `sample_count = good_count + uncertain_count + bad_count`; `usable_count <= good_count`, `out_of_range_count <= sample_count`. Source quality и `out_of_range_count` считаются независимо, поэтому второй может пересекаться с первой категорией. `usable_count` требует GOOD и отсутствия OUT_OF_RANGE. Нулевые counts не превращаются в отсутствующую строку: строка создаётся при наличии raw samples.

Duration/count поля `machine_metric_bucket_1m` неотрицательны; `shift_id` и `shift_date` либо оба `NULL`, либо оба заполнены. Worker проверяет, что business-state durations суммируются в `covered_duration_ms`, а loss duration каждой state/reason не превышает длительность этого state. `machine_loss_bucket_1m` хранит только положительные строки состояний `IDLE`, `DOWN`, `SETUP`, `PLANNED_STOP`.

Current API получает `calculatedState` и currency из `machine_current_state`, а `effectiveState` и ссылки overlay — из единственного открытого `machine_effective_state_interval`. Partial unique index по `machine_id WHERE effective_to IS NULL` гарантирует максимум одну текущую строку. Аналогичный индекс действует на calculated timeline. Один indexed query возвращает оба слоя без дублирования effective state в отдельной current-таблице.

Все интервалы полуоткрытые. Закрытая строка требует `effective_to > effective_from`; cross-row отсутствие дыр и пересечений проверяет worker перед публикацией. Current interval может быть открытым. При одинаковом состоянии граница сохраняется только когда этого требуют изменения ссылок/источника в effective timeline; calculated timeline остаётся state-only.

Bucket хранит `bucket_start` в UTC с минутным выравниванием и описывает `[bucket_start, bucket_start + 1 minute)`. Minute bucket публикуется только после закрытия минуты. `shift_id` и `shift_date` либо оба заполнены, либо оба `NULL` для времени вне смены. `sample_count = good_count + uncertain_count + bad_count`; `out_of_range_count` — пересекающийся diagnostic count, а не четвёртая категория качества.

Поскольку PostgreSQL считает `NULL` различными в обычном unique index, `machine_loss_bucket_1m` использует `UNIQUE NULLS NOT DISTINCT (machine_id, bucket_start, state, loss_reason_id)` (PostgreSQL 16). Дополнительный sentinel-reason не создаётся.

## Индексы

Стартовый набор следует фактическим запросам frontend:

| Таблицы | Индекс | Запрос |
| --- | --- | --- |
| `signal_current_value` | `(machine_id, signal_id)` | Current значения машины; PK `signal_id` обслуживает чтение отдельного сигнала |
| Обе interval tables | PK `(machine_id, effective_from)` и уникальный partial `(machine_id) WHERE effective_to IS NULL` | Timeline периода и current interval |
| `signal_numeric_rollup_1m` | PK `(signal_id, bucket_start)` | Ряд одного или нескольких выбранных сигналов за диапазон |
| `machine_metric_bucket_1m` | PK `(machine_id, bucket_start)` | Диапазон машины и агрегаты |
| `machine_loss_bucket_1m` | UNIQUE NULLS NOT DISTINCT `(machine_id, bucket_start, state, loss_reason_id)` | Loss range, Pareto и chronometry; ведущие колонки покрывают machine/time |
| Machine metric/loss buckets | `(shift_id, shift_date, machine_id, bucket_start)` | Аналитика по выбранной смене и дате |
| `dirty_range` | Partial queue index по priority/created time для `PENDING`/`RETRY`; lease index по `lease_until` для `RUNNING` | Claim и возврат просроченной работы |
| `state_recalculation_job` | PK по job ID; partial unique `(machine_id)` для `PENDING`/`RUNNING` | Polling job и один активный user job на Machine |
| `machine_evaluation_deadline` | PK `machine_id`, индекс `(deadline_at, machine_id)` | Claim due deadlines в event-time порядке |

Отдельные line/enterprise summary tables, JSON indexes, индексы по метрикам и индексы только под редкие фильтры не создаются. Machine bucket сначала ограничивается выбранным составом машин; `shift_id + shift_date` используется для сменных выборок. Новые индексы добавляются после измеренного query plan и benchmark.

## Фоновая работа и staging

`analytics.dirty_range` — durable work queue с `id`, `machine_id`, нормализованными границами, cause, priority, status, attempts и lease. Очередь объединяет пересекающиеся/соседние ожидающие ranges одной Machine. Активный leased range неизменяем; новые hints создают последующую работу. `FOR UPDATE SKIP LOCKED` позволяет нескольким workers брать разные машины, а per-machine lease запрещает параллельную публикацию одной машины.

`analytics.state_recalculation_job` остаётся адресуемой сущностью API с UUID, статусом, диапазоном и progress. Она связывается с work queue, но не заменяет внутренние dirty ranges. `analytics.machine_evaluation_deadline` хранит одну ближайшую строку на Machine; deadline worker создаёт обычную dirty work.

Минимальные поля управляющих таблиц:

```text
dirty_range:
  id BIGINT PK; machine_id UUID FK; dirty_from/dirty_to TIMESTAMPTZ(3)
  cause VARCHAR(32); priority SMALLINT; status VARCHAR(16)
  recalculation_job_id UUID NULL FK analytics.state_recalculation_job(id)
  attempts INTEGER; lease_owner VARCHAR(128) NULL; lease_until TIMESTAMPTZ(3) NULL
  created_at TIMESTAMPTZ(3); CHECK dirty_to > dirty_from
  status CHECK IN (QUEUED, RUNNING, RETRYABLE, FAILED)
  dirty_from inclusive; dirty_to exclusive

state_recalculation_job:
  id UUID PK; machine_id UUID FK; scope VARCHAR(16)
  requested_from/requested_to/effective_from/effective_to TIMESTAMPTZ(3) NULL
  status VARCHAR(16); progress NUMERIC(5,4); created_at/started_at/completed_at TIMESTAMPTZ(3)
  status CHECK IN (PENDING, RUNNING, SUCCEEDED, FAILED); CHECK progress BETWEEN 0 AND 1
  scope CHECK IN (PERIOD, ALL)
  requested_from/to are both set for PERIOD and both NULL for ALL

machine_evaluation_deadline:
  machine_id UUID PK/FK; deadline_at TIMESTAMPTZ(3); reason VARCHAR(32)
  lease_owner VARCHAR(128) NULL; lease_until TIMESTAMPTZ(3) NULL
  updated_at TIMESTAMPTZ(3)
```

`cause` хранит `TELEMETRY`, `DEADLINE`, `RULE_CHANGE`, `INCIDENT_CHANGE` или `USER_RECALCULATION`; deadline `reason` хранит `SIGNAL_STALE`, `RULE_ACTIVATION`, `RULE_RELEASE` или `MACHINE_OFFLINE`. Эти закрытые коды и статусы хранятся в `VARCHAR` с `CHECK`, не в PostgreSQL native enum. Liquibase создаёт `state_recalculation_job` до `dirty_range`, чтобы FK на пользовательский job был доступен при создании очереди. Для PERIOD from/to обязательны, для ALL отсутствуют; эффективные границы заполняются после нормализации.

Рабочие результаты сохраняются в обычных durable staging tables по одному shape на output table и с ключом `dirty_range_id` перед бизнес-ключом. У staging нет FK на `dirty_range`: большая публикация не запускает каскадное удаление всех staged rows в своей транзакции. Staging имеет те же business keys и typed fields, что публикуемые таблицы, плюс work-item ID. До publication stage проверяется на coverage, порядок интервалов, отсутствие дыр/пересечений и допустимые суммы durations. После успеха или отмены staging удаляется ограниченными chunks; неполный staging после crash безопасно пересоздаётся из committed raw и durable work. Успешный work item удаляется в publication transaction после обновления projection и API job; FAILED сохраняется до решения оператора и блокирует retention. Отдельная ограниченная очистка удаляет staging без соответствующего активного work item. Current signal row обновляется отдельным условным idempotent UPSERT по ordering tuple и не ждёт полной исторической публикации.

## Публикация

Длительное чтение raw, replay и построение нового результата выполняются вне write transaction активных проекций. В одной короткой транзакции worker:

1. Проверяет, что work-item и input checkpoint всё ещё актуальны.
2. Удаляет старые строки только для нормализованного диапазона и этой Machine/Signal.
3. Вставляет соответствующие validated stage rows в timeline и затронутые минутные buckets.
4. Обновляет `machine_current_state`, `data_through`, `calculated_at`, `recalculating` и статус связанного job.
5. Удаляет успешно опубликованный work item и фиксирует транзакцию.

Для ручных incident changes обновляются только effective timeline, machine metrics и loss buckets; raw, signal current, signal rollup и calculated state intervals остаются прежними. Для telemetry `signal_current_value` обновляется отдельным условным UPSERT после ingest commit; dirty worker заменяет calculated/effective timelines и затронутые numeric/machine/loss minute projections. Граница публикации всегда полная для рассчитанного диапазона.

PostgreSQL MVCC оставляет readers на прежних committed rows до commit и показывает новые целиком после него. Read API не блокирует ingestion ожиданием расчёта; `data_through`, `calculated_at`, `stale`, `partial` и `recalculating` описывают currency результата.
