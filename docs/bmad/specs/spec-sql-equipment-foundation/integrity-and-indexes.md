# Ограничения целостности и стартовые индексы

## Владение и уникальность

| Table | Constraint |
| --- | --- |
| `enterprise` | `UNIQUE (code)` |
| `production_line` | `UNIQUE (enterprise_id, code)` и технический `UNIQUE (enterprise_id, id)` |
| `machine` | `UNIQUE (enterprise_id, code)`, partial unique `(enterprise_id, inventory_no) WHERE inventory_no IS NOT NULL` |
| `component` | `UNIQUE (machine_id, code)` и технический `UNIQUE (machine_id, id)` |
| `telemetry_signal` | `UNIQUE (machine_id, code)` и технический `UNIQUE (machine_id, id)` |
| `shift` | `UNIQUE (enterprise_id, code)` |

Machine использует составной FK `(enterprise_id, line_id) → production_line(enterprise_id, id)`. Component parent и TelemetrySignal component используют `(machine_id, component_id) → component(machine_id, id)`. Это защищает границы владельца без trigger.

## Локальные CHECK

- Все status: `ACTIVE` или `DISABLED`.
- Все `sort_order` и `display_order`: неотрицательные.
- `parameters`: верхний JSON-тип `array`.
- Machine: `nominal_rate` и `production_unit_code` заданы парой; `nominal_rate > 0`; `commissioning_year` четырёхзначный; `line_id` и `sort_order` заданы парой.
- Component: `id <> parent_component_id`; `kind` входит в согласованный каталог.
- TelemetrySignal: разрешённые пары `signal_kind/value_type`; интервалы положительны; `stale_after_ms >= expected_interval_ms`; `valid_min <= valid_max`; границы допустимы только для числовых типов; `custom_semantic_code` задан только и обязательно при `semantic_code = 'CUSTOM'`.
- Shift: `valid_to IS NULL OR valid_to > valid_from`.

Формат стабильных code, лимит display parameters, цикл Component, пересечение Shift, readiness и неизменяемость полей проверяет приложение. Такие проверки требуют текущего состояния нескольких таблиц или правил времени и не дублируются сложными triggers.

## Атомарные конкурентные операции

- Назначение Machine выполняется условным `UPDATE ... WHERE line_id IS NULL`; пакет блокирует выбранные Machine в детерминированном порядке и фиксируется целиком либо не фиксируется.
- Переназначение parent Component сначала блокирует owning Machine row, затем выполняет recursive CTE и `UPDATE`; все изменения одного дерева сериализованы.
- Создание и изменение Shift schedule сначала блокирует owning Enterprise row, затем проверяет пересечения всех применимых Shift; параллельные расписания одного Enterprise не проходят write-skew.
- Активация Machine повторяет readiness внутри одной транзакции.
- Обновление смысловых полей TelemetrySignal берёт exclusive transaction advisory lock, производный от `signal_id`, и проверяет неистекающий `telemetry.signal_usage`; writer берёт shared lock того же ключа до регистрации первого использования. Generator не получает `UPDATE` на equipment.
- Обновление границ Shift проверяет существование аналитических данных в той же Enterprise-serialized транзакции.
- Обновление `enterprise.timezone` под lock Enterprise проверяет durable `telemetry.signal_usage` через цепочку Signal → Machine → Enterprise, а также incidents, generator runs и projections; после появления любого такого факта timezone неизменяема независимо от raw retention.
- Общего `row_version` в MVP нет; независимые обычные updates используют last-committed-write-wins.

## Стартовые read indexes

```text
production_line  (enterprise_id, status, sort_order, code)
machine          (enterprise_id, line_id, status, sort_order, code)
component        (machine_id, parent_component_id, status, sort_order, code)
telemetry_signal (machine_id, status, display_order, code)
shift            (enterprise_id, status, valid_from, valid_to)
```

Индексы уникальности и FK учитываются при проверке фактического набора: дублирующий индекс не создаётся. Новые индексы добавляются только под подтверждённый query shape и проверяются `EXPLAIN (ANALYZE, BUFFERS)` на репрезентативных данных.
