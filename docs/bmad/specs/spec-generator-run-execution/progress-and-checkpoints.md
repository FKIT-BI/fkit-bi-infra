# Progress и checkpoints

## Run detail

| Поле | Семантика |
|---|---|
| `status`, `mode`, `attemptNo` | Lifecycle и номер execution attempt |
| `requestedAt`, `scheduledStartAt` | Время команды и будущего старта |
| `startedAt`, `finishedAt` | Фактические runtime boundaries |
| `eventFrom`, `eventTo` | Запрошенная/вычисленная event-time coverage |
| `currentPhaseCode`, `cycleNumber` | Текущая позиция Scenario |
| `generatedThrough` | Максимальная полностью обработанная event-time boundary |
| `progressPercent` | `0..100` только для bounded coverage |
| `generatedMeasurements` | Сформированные measurements |
| `writtenMeasurements` | Подтверждённые PostgreSQL measurements |
| `droppedMeasurements` | Потерянные при buffer/retry/stop timeout |
| `failedBatches` | Неуспешные batch write attempts |
| `lastSuccessfulWriteAt` | Последний подтверждённый commit |
| `stopRequestedAt` | Принятая stop command |
| `failure` | Code, bounded message, retryable и failedAt |

`progressPercent` вычисляется по event-time coverage, а не количеству строк. Он `null` для unbounded realtime и для ожидающего Scheduled Run. Counters монотонны в пределах Run и не сбрасываются при retry.

## Historical chunks

Historical range делится на последовательные пятиминутные event-time chunks, начиная с `from`; последний chunk может быть короче. Внутри chunk measurements сортируются детерминированно и делятся на batches не более 1000 строк.

Stable batch identity выводится из `runId`, machine/scope, chunk start и batch ordinal. Retry незавершённого chunk создаёт те же producer batch IDs, поэтому принятые batches возвращаются как duplicate success, а отсутствующие дописываются.

Checkpoint сохраняется только после подтверждения всех batches chunk. Он содержит как минимум:

- completed event-time boundary;
- cycle/phase position;
- deterministic sequence/batch position;
- aggregate counters на этой границе.

Crash до checkpoint не объявляет chunk завершённым. Crash после checkpoint начинает следующий chunk. Checkpoint и status update выполняются короткими транзакциями отдельно от raw batch transaction.

## Coverage и overlap

Подтверждённый historical chunk формирует durable generator coverage по Machine и event-time range. Новый Run с пересечением отклоняется `409 HISTORICAL_RANGE_OVERLAP`, чтобы не создавать вторые raw-факты. Пользователь может продолжить stopped range новым Run от `generatedThrough`; автоматическое удаление/replace coverage отсутствует.

Realtime gaps не преобразуются в historical checkpoint. Их видно по skipped/dropped counters и Analytics freshness.

## Analytics context

Run response возвращает `enterpriseId`, `machineIds`, фактические `eventFrom`, `generatedThrough` и nullable `eventTo`. Эти поля позволяют frontend открыть Analytics API. Generator не читает `dataThrough` и не вычисляет готовность аналитики.
