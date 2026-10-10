# Текущая проекция сигнала

## `signal_current_value`

Проекция обновляется асинхронно после commit ingest batch и содержит две группы данных:

| Группа | Поля |
| --- | --- |
| Идентичность | `signalId`, `machineId` |
| Last received | `lastReceivedObservedAt`, `lastReceivedAt`, `lastReceivedBatchId`, `lastReceivedOrdinal`, типизированное value, `sourceQuality`, `validationFlags` |
| Last usable | `lastUsableObservedAt`, `lastUsableReceivedAt`, `lastUsableBatchId`, `lastUsableOrdinal`, типизированное value |
| Проекция | `projectedAt` |

Первичный ключ — `signalId`. `machineId` денормализован для выборки всех текущих сигналов машины без чтения raw.

Freshness не хранится в строке, потому что оно изменяется с течением времени даже без новых событий. API и evaluator вычисляют его из `lastUsableObservedAt`, текущего `TelemetrySignal.staleAfterMs` и reference time.

## Порядок замещения

Last received сравнивается лексикографически:

```text
(observedAt, ingestBatchId, ordinal)
```

Новая строка заменяет проекцию только если её ключ больше текущего. Last usable применяет то же правило, но рассматривает только usable measurements.

Поэтому historical или late data:

- сохраняется в raw;
- создаёт dirty window для своего event-time диапазона;
- не откатывает current projection к более старому значению.

## Current API DTO

Ответ текущего сигнала включает:

```text
signalId
lastReceivedValue
lastReceivedObservedAt
lastReceivedAt
quality
validationFlags
lastUsableValue
lastUsableObservedAt
freshness: NO_DATA | FRESH | STALE
dataThrough
calculatedAt
stale
```

Верхнеуровневый `stale` сообщает lag самой аналитической проекции относительно SLO; `freshness` сообщает актуальность конкретного сигнала. Это разные признаки.

Current state машины дополнительно возвращает `lastTelemetryObservedAt`. Запрос не ждёт ingestion или calculation worker: при отставании он возвращает последнюю committed projection и её currency metadata.
