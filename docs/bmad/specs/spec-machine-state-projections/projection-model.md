# Модель state projections

## Coverage

Первый переход Machine в `ACTIVE` фиксирует неизменяемый `coverageFrom`. До него состояние не определено. С него отсутствие telemetry даёт `OFFLINE` по системной политике.

Опубликованная историческая область:

```text
[coverageFrom, dataThrough)
```

`dataThrough` — исключительная UTC-minute boundary, до которой применены все ingest batches, известные worker на момент публикации. Это не обещание отсутствия будущей late telemetry: последующий raw может скорректировать уже опубликованный диапазон.

## `machine_current_state`

Одна строка на Machine:

```text
machineId
coverageFrom
state
stateSince
matchedRuleId?
evaluationQuality
lastTelemetryObservedAt?
dataThrough
calculatedAt
recalculating
```

`stateSince` — точное начало непрерывного текущего MachineState. Current evaluation может быть свежее minute-aligned historical `dataThrough`; это отражают `lastTelemetryObservedAt` и `calculatedAt`.

## `machine_state_interval`

```text
machineId
effectiveFrom
effectiveTo?
state
detectedAt
calculatedAt
```

Интервал полуоткрытый `[effectiveFrom,effectiveTo)`. У продолжающегося current interval `effectiveTo=null`; для исторических duration/rollup он используется не дальше published `dataThrough`.

Timeline делится только при изменении `state`. Изменение matched rule или evaluation quality при том же state не создаёт новый интервал. Соседние интервалы одинакового state объединяются; нулевые интервалы запрещены.

Внутри coverage выполняются:

- строгая сортировка по `effectiveFrom`;
- отсутствие пересечений и дыр;
- `effectiveTo > effectiveFrom` для закрытой строки;
- максимум один open interval, последний в timeline.

## Порядок одинакового event time

Для одного Signal значения разрешаются по ключу:

```text
(observedAt, ingestBatchId, ordinal)
```

Все значения Machine с одинаковым `observedAt` сначала образуют единый snapshot, затем evaluator выполняется один раз. Порядок строк в batch не создаёт промежуточные состояния.

## Read API

```text
GET /api/machines/{machineId}/current-state
GET /api/machines/{machineId}/state-intervals?from=...&to=...
```

Current response использует только committed projection. Timeline endpoint требует ограниченный период; точная пагинация и представление clipped boundaries определяются итоговым OpenAPI.
