# Семантика evaluator

## Трёхзначная логика

| Expression | Результат |
| --- | --- |
| `NOT TRUE/FALSE/UNKNOWN` | `FALSE/TRUE/UNKNOWN` |
| `ALL` с хотя бы одним `FALSE` | `FALSE` |
| `ALL` только с `TRUE` | `TRUE` |
| Остальной `ALL` | `UNKNOWN` |
| `ANY` с хотя бы одним `TRUE` | `TRUE` |
| `ANY` только с `FALSE` | `FALSE` |
| Остальной `ANY` | `UNKNOWN` |

Evaluator строит snapshot last usable values на event-time точку `T`. `NO_DATA` и `STALE` входят в AST как `UNKNOWN`.

## Порядок выбора

1. Если для Machine выполняется system offline policy, вернуть `OFFLINE`.
2. Оценить release активного user rule.
3. Оценить остальные rules по убыванию unique priority.
4. Higher-priority rule с непрерывным TRUE в течение `activationDelayMs` preempts текущий.
5. Если активное rule освобождено, выбрать первый активированный candidate.
6. Если candidate нет, вернуть `defaultState`.

Одновременно публикуется ровно одно состояние.

## Activation, release и hysteresis

Enter condition должен оставаться `TRUE` непрерывно `activationDelayMs`; `FALSE` или `UNKNOWN` сбрасывает timer. При нулевой delay effective activation совпадает с началом TRUE.

Если `exitCondition` задан, он должен быть `TRUE` непрерывно `releaseDelayMs`. Если он отсутствует, выходной кандидат начинается при `enterCondition = FALSE` или `UNKNOWN`. Возврат к удерживающему значению сбрасывает release timer.

Разные enter/exit thresholds задают hysteresis. Например, enter `speed >= 100`, exit `speed < 70` удерживает rule при `70 <= speed < 100`.

## Default и evaluation quality

`UNKNOWN` не является MachineState. Если ни одно rule не активировано, используется `defaultState`.

Результат имеет:

```text
state
effectiveFrom
detectedAt
matchedRuleId
evaluationQuality: COMPLETE | DEGRADED
```

`matchedRuleId = null` для `OFFLINE` и default state. `DEGRADED` означает, что хотя бы один релевантный evaluated branch получил `UNKNOWN` и результат выбран при неполном snapshot; иначе `COMPLETE`.

`effectiveFrom` — event-time начало состояния после выполнения delay. `detectedAt` — processing timestamp публикации. Late data может дать `detectedAt` значительно позже `effectiveFrom`.
