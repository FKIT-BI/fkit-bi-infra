# Процесс перерасчёта

## Dirty windows

После commit ingest batch затронутые measurements группируются по Machine. Исходный диапазон расширяется наружу:

```text
dirtyFrom = floor(minObservedAt, UTC minute)
dirtyTo   = ceil(maxObservedAt, UTC minute)
```

Пересекающиеся и соседние windows одной Machine объединяются. Перед evaluation левая граница расширяется до предыдущей устойчивой state boundary и достаточного signal/timer context, но не раньше `coverageFrom`. Правая граница MVP — текущий `dataThrough`; фиксированный хвост не используется.

Рабочая запись хранит как минимум `machineId`, normalized from/to, cause, priority, status, attempts и lease. Realtime windows имеют приоритет над historical/user recalculation work.

## Фоновый расчёт и staging

Длинный replay выполняется без write transaction активной timeline:

1. Получить per-machine lease.
2. Зафиксировать input checkpoint и target `dataThrough`.
3. Восстановить левый snapshot и timers.
4. Replay raw/event deadlines до target boundary.
5. Нормализовать state-only intervals.
6. Записать результат в job staging.
7. Проверить coverage, отсутствие дыр/пересечений и граничное соединение с незаменяемой timeline.
8. Короткой транзакцией заменить active interval range, обновить current projection, coverage/checkpoints и job status.
9. Асинхронно очистить staging.

PostgreSQL MVCC позволяет readers видеть старую committed timeline до commit. `recalculating=true` сообщает, что для Machine готовится новый результат. Частичное staging никогда не участвует в read API.

Если во время расчёта пришла новая telemetry, она создаёт следующий dirty window. Опубликованный результат остаётся eventual-consistent и затем актуализируется повторно.

## Изменение rules

После сохранения новой MachineStateConfig current state оценивается текущими rules. История автоматически целиком не переписывается: пользователь запускает `PERIOD` или `ALL`. Поскольку configuration history отсутствует, такой replay использует текущую конфигурацию на всём выбранном диапазоне.

## User recalculation

```text
POST /api/machines/{machineId}/state-recalculations
GET  /api/state-recalculations/{recalculationId}
```

Запрос периода:

```json
{"scope":"PERIOD","from":"...","to":"..."}
```

Полный запрос:

```json
{"scope":"ALL"}
```

`PERIOD` расширяется до UTC-minute boundaries и evaluator context. `ALL` использует `[coverageFrom,current dataThrough)`. Job возвращает requested/effective ranges, progress, timestamps, error и status:

```text
PENDING | RUNNING | SUCCEEDED | FAILED
```

На Machine допускается один active user recalculation; второй получает `409 RECALCULATION_ALREADY_RUNNING`. После `FAILED` пользователь может создать новый job. HTTP не ждёт выполнения.

## Recovery и идемпотентность

Workers используют `FOR UPDATE SKIP LOCKED` и expiring lease. Crash до publication оставляет active projection неизменной; staging можно продолжить или очистить. Crash после commit считается опубликованным по job/checkpoint. Повторная публикация проверяет captured checkpoint и не создаёт дубликаты intervals.
