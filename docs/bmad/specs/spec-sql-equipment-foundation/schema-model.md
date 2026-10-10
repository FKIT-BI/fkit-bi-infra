# Физическая модель конфигурации

## Разделение схем

| Schema | Ответственность |
| --- | --- |
| `equipment` | Предприятия, линии, машины, компоненты, сигналы, смены и их справочники |
| `telemetry` | Batch ingestion, raw measurements и текущие значения сигналов |
| `analytics` | Состояния машин, rollup, метрики, dirty ranges и перерасчёты |
| `incident` | Причины потерь и ручные инциденты |
| `generator` | Сценарии, runs, snapshots и прогресс |

Этот блок создаёт все schemas, но доменные таблицы — только в `equipment`. Таблицы остальных schemas добавляются последующими спецификациями и changeset.

## Общие типы

- `id`: `UUID` без database default; значение назначает backend.
- `created_at`, `updated_at`: `TIMESTAMPTZ(3) NOT NULL DEFAULT CURRENT_TIMESTAMP`.
- Локальное время Shift: `TIME(0) WITHOUT TIME ZONE`.
- Локальная дата Shift: `DATE`.
- Интервалы конфигурации: `BIGINT` в миллисекундах.
- Порядок отображения: `INTEGER` с неотрицательным `CHECK`.
- Display parameters: `JSONB NOT NULL DEFAULT '[]'::jsonb` с проверкой верхнего JSON-типа `array`; внутренняя типизация и лимит 100 проверяются приложением.

## Справочники

### `equipment.signal_semantic`

| Column | Type | Правило |
| --- | --- | --- |
| `code` | `VARCHAR(64)` | PK, стабильный машинный код |
| `name` | `VARCHAR(200)` | Отображаемое имя |
| `description` | `TEXT NULL` | Пояснение семантики |
| `status` | `VARCHAR(16)` | `ACTIVE` или `DISABLED` |
| `created_at`, `updated_at` | `TIMESTAMPTZ(3)` | Техническое время |

Начальный data changeset содержит согласованный каталог от `TEMPERATURE` до `CUSTOM`. Disabled-код остаётся допустимым для истории, но не выбирается в новой конфигурации.

### `equipment.measurement_unit`

| Column | Type | Правило |
| --- | --- | --- |
| `code` | `VARCHAR(64)` | PK, стабильный машинный код |
| `name` | `VARCHAR(200)` | Отображаемое имя |
| `symbol` | `VARCHAR(32) NULL` | Краткое отображение |
| `quantity_code` | `VARCHAR(64) NULL` | Группа совместимости единиц |
| `status` | `VARCHAR(16)` | `ACTIVE` или `DISABLED` |
| `created_at`, `updated_at` | `TIMESTAMPTZ(3)` | Техническое время |

`production_unit_code` и `unit_code` используют один справочник. Физическое преобразование единиц в MVP не выполняется; совместимость проверяет доменный сервис.

## Конфигурационные таблицы

### `equipment.schema_release`

```text
singleton BOOLEAN PK CHECK (singleton)
release VARCHAR(64)
updated_at TIMESTAMPTZ(3)
```

Liquibase поддерживает ровно одну строку `singleton = true`. Таблица не является историей migrations; она даёт Analytics и Generator простой fail-fast compatibility check при readiness.

### `equipment.enterprise`

```text
id UUID PK
code VARCHAR(64)
name VARCHAR(200)
timezone VARCHAR(100)
status VARCHAR(16)
created_at TIMESTAMPTZ(3)
updated_at TIMESTAMPTZ(3)
```

Timezone хранится как IANA ZoneId и проверяется Java. После появления временных эксплуатационных данных её изменение блокирует доменный сервис.

### `equipment.production_line`

```text
id UUID PK
enterprise_id UUID FK
code VARCHAR(64)
name VARCHAR(200)
sort_order INTEGER
status VARCHAR(16)
created_at TIMESTAMPTZ(3)
updated_at TIMESTAMPTZ(3)
```

### `equipment.machine`

```text
id UUID PK
enterprise_id UUID FK
line_id UUID NULL
code VARCHAR(64)
name VARCHAR(200)
machine_type VARCHAR(128) NULL
inventory_no VARCHAR(128) NULL
manufacturer VARCHAR(200) NULL
model VARCHAR(200) NULL
commissioning_year SMALLINT NULL
nominal_rate NUMERIC(20,6) NULL
production_unit_code VARCHAR(64) NULL FK
sort_order INTEGER NULL
status VARCHAR(16)
parameters JSONB
created_at TIMESTAMPTZ(3)
updated_at TIMESTAMPTZ(3)
```

`line_id` и `sort_order` одновременно отсутствуют у свободной машины и одновременно присутствуют после назначения. Единственный допустимый переход назначения — `line_id: null → value`.

### `equipment.component`

```text
id UUID PK
machine_id UUID FK
parent_component_id UUID NULL
code VARCHAR(64)
name VARCHAR(200)
kind VARCHAR(64)
sort_order INTEGER
status VARCHAR(16)
parameters JSONB
created_at TIMESTAMPTZ(3)
updated_at TIMESTAMPTZ(3)
```

`kind` использует закрытый согласованный `ComponentKind`; отдельная таблица видов компонентов не создаётся.

### `equipment.telemetry_signal`

```text
id UUID PK
machine_id UUID FK
component_id UUID NULL
code VARCHAR(64)
name VARCHAR(200)
description TEXT NULL
value_type VARCHAR(16)
signal_kind VARCHAR(16)
semantic_code VARCHAR(64) FK
custom_semantic_code VARCHAR(64) NULL
unit_code VARCHAR(64) NULL FK
expected_interval_ms BIGINT NULL
stale_after_ms BIGINT NULL
valid_min NUMERIC NULL
valid_max NUMERIC NULL
featured BOOLEAN
display_order INTEGER NULL
status VARCHAR(16)
created_at TIMESTAMPTZ(3)
updated_at TIMESTAMPTZ(3)
```

Блокировка смысловых полей после первого raw measurement проверяется доменным сервисом в транзакции, а не trigger.

Для owner-preserving FK проекции `telemetry.signal_current_value` таблица также имеет технический `UNIQUE (machine_id, id)`; эта пара не меняет бизнес-уникальность Signal.

### `equipment.shift`

```text
id UUID PK
enterprise_id UUID FK
code VARCHAR(64)
name VARCHAR(200)
start_local_time TIME(0)
end_local_time TIME(0)
valid_from DATE
valid_to DATE NULL
sort_order INTEGER
status VARCHAR(16)
created_at TIMESTAMPTZ(3)
updated_at TIMESTAMPTZ(3)
```

Экземпляры смен не хранятся отдельной таблицей. Пересечения recurring intervals, DST и блокировка использованных границ проверяются единым доменным алгоритмом.
