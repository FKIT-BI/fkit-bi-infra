# Модели поведения сигналов

## Общая форма

Каждое поведение относится к одному `signalId` target Machine и содержит:

| Поле | Правило |
|---|---|
| `signalId` | Существующий активный signal из snapshot |
| `generationIntervalMs` | Целое число не меньше 1000 |
| `model` | Один совместимый discriminator |
| `parameters` | Типизированная конфигурация выбранной модели |
| `noise` | Необязательный ограниченный шум для numeric model |
| `missingProbability` | Необязательное значение `0..1`; пропуск означает отсутствие measurement |
| `sourceQuality` | `GOOD|UNCERTAIN|BAD`, default `GOOD` |
| `seedOverride` | Необязательный deterministic seed конкретного behavior |

Значение после model и noise приводится к типу TelemetrySignal. Нарушение `validMin/validMax` не обрезается: raw сохраняется с `OUT_OF_RANGE`. `NaN`, infinity, null и несовместимый тип не генерируются.

## Каталог MVP

| Тип сигнала | Model | Минимальные параметры |
|---|---|---|
| Numeric GAUGE | `CONSTANT` | `value` |
| Numeric GAUGE | `UNIFORM` | `min`, `max` |
| Numeric GAUGE | `NORMAL` | `mean`, `standardDeviation`, optional clamp |
| Numeric GAUGE | `RAMP` | `from`, `to`, `durationMs`, `repeat` |
| Numeric GAUGE | `SINE` | `center`, `amplitude`, `periodMs`, optional phase |
| Numeric COUNTER | `COUNTER_RATE` | `initialValue`, `incrementPerSecond`, optional reset threshold/value |
| BOOLEAN | `CONSTANT` | `value` |
| BOOLEAN | `PULSE` | `onDurationMs`, `offDurationMs`, initial value |
| BOOLEAN | `BERNOULLI` | `trueProbability` |
| STRING/STATE | `CONSTANT` | `value` |
| STRING/STATE | `SEQUENCE` | non-empty values и dwell duration |

Behavior model обязан соответствовать `TelemetrySignal.valueType` и `sequenceKind`. `COUNTER_RATE` разрешён только для numeric `COUNTER`; string models не применяются к numeric сигналам.

## Base behavior и phase overrides

Machine target хранит optional base behavior каждого используемого Signal. Phase перечисляет только отличия:

| Состояние override | Effective behavior |
|---|---|
| `REPLACE` с полной configuration | Используется configuration phase |
| `DISABLE` | Measurement не создаётся |
| Override отсутствует, base существует | Используется base behavior |
| Override и base отсутствуют | Measurement не создаётся |

`REPLACE` всегда содержит полную типизированную behavior configuration; частичное объединение `parameters`, `noise`, interval или quality запрещено. Один уровень base/override уменьшает payload, не создавая цепочек наследования.

При создании Run compiler материализует effective behavior каждой пары phase/signal в immutable snapshot. Runtime не разрешает наследование динамически.

Физические корреляции между сигналами, component-level models и выражения могут позднее компилироваться в тот же набор per-signal behaviors. Они не меняют raw writer contract.

## Детерминизм

Run получает один `randomSeed`. Для каждого stable набора `machineId + signalId + phaseCode + cycle` generator выводит sub-seed; JSON array order и порядок worker threads не должны менять значения. `seedOverride` заменяет sub-seed только для указанного effective behavior. Одинаковые snapshot, seed и event-time range дают одинаковую последовательность measurements.
