# Команды и восстановление

## Create Run и HTTP-idempotency

`POST /runs` требует `Idempotency-Key`. Generator сохраняет key, canonical request hash и созданный `runId` одной транзакцией.

- Тот же key и тот же canonical body возвращают исходный response без нового Run.
- Тот же key и другой body возвращают `409 IDEMPOTENCY_KEY_REUSED`.
- Key хранится не меньше самого Run.
- Equipment/scenario validation выполняется до создания Run, но повтор успешной команды не зависит от последующих изменений current configuration.

## Stop

Stop command идемпотентна:

| Текущее состояние | Результат |
|---|---|
| `SCHEDULED`, `QUEUED` | `CANCELLED`, execution не начинается |
| `RUNNING` | `STOP_REQUESTED`, затем `STOPPED` |
| `STOP_REQUESTED` | Возвращается текущий Run |
| Terminal | Возвращается текущее terminal состояние |

После `STOP_REQUESTED` новые ticks не планируются. Текущая raw transaction завершается либо откатывается; готовый buffer flush выполняется один раз с bounded timeout. Остаток после timeout отбрасывается, увеличивает `droppedMeasurements`, и Run всё равно переходит `STOPPED`.

## Failure и retry

Failure содержит stable `code`, безопасное bounded `message`, `failedAt` и `retryable`. Validation errors, ownership/status conflicts, historical overlap и `SCHEDULE_MISSED` не retryable. Временная PostgreSQL/network/resource ошибка может быть retryable после завершения внутреннего bounded retry.

`POST /runs/{runId}/retry` разрешён только для `FAILED` с `retryable=true`:

- сохраняет тот же `runId`, snapshot, seed и producer stream;
- увеличивает `attemptNo`;
- сохраняет предыдущую attempt history;
- переводит Run в `QUEUED`.

Historical Run продолжает с последнего checkpoint и повторяет незавершённый chunk deterministic batch IDs. Realtime Run продолжает от текущего wall clock; период отказа остаётся gap. Scheduled Run, не начавшийся из-за non-retryable readiness/misfire, требует создания нового Run.

Одновременные retry/stop защищаются atomic status transition: только одна команда меняет ожидаемое состояние, остальные получают актуальный Run или `409 RUN_STATE_CONFLICT`.

## Polling

- Active Run detail: ориентир 2 seconds.
- Scheduled и terminal list: ориентир 10 seconds.
- `Retry-After` может увеличить период при pressure.
- SSE, WebSocket и long polling не входят в MVP.

`COMPLETED` подтверждает только окончание raw generation. Frontend после перехода к Analytics показывает её собственные `dataThrough`, `stale` и `recalculating`; generator не блокирует завершение на calculation workers.
