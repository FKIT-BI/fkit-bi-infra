# Writer protocol

## Граница интеграции

Generator пишет через интерфейс `TelemetrySink.writeBatch`; JDBC-реализация сохраняет header и measurements в общей PostgreSQL. Управляющий OpenAPI generator не используется для передачи каждого измерения.

Логический пакет:

```text
producerId
producerBatchId
producerSequence
generatorRunId?
mode: REALTIME | HISTORICAL
measurements[1..1000]
payloadHash
```

Измерение содержит `signalId`, `observedAt`, ровно одно типизированное `value` и необязательное source quality. `receivedAt` назначает PostgreSQL, count и границы event time вычисляет writer. `producerSequence` возрастает внутри одного producer stream; для generator таким stream является run.

`payloadHash` — SHA-256 формата `TELEMETRY_BATCH_V1`. Byte stream начинается с 18 фиксированных ASCII bytes `TELEMETRY_BATCH_V1`, затем строго в указанном порядке идут: `producerId`, `producerBatchId`, `producerSequence`, optional `generatorRunId`, numeric `mode`, unsigned 32-bit число measurements и measurements в исходном ordinal order. Для каждой строки идут `signalId`, `observedAt`, value-type discriminator (`1=DOUBLE`, `2=LONG`, `3=BOOLEAN`, `4=STRING`), typed value и уже нормализованный numeric source quality. Целые числа кодируются big-endian, UUID — 16 network-order bytes, timestamp — signed int64 epoch milliseconds, boolean — один byte `0/1`, double — IEEE-754 binary64 bits, string — UTF-8 с unsigned 32-bit byte length, optional field — один presence byte `0/1` перед значением. Server-assigned поля, вычисленные count/min/max и validation flags не входят. `NaN`, infinity и timestamp точнее миллисекунды отклоняются до hashing; отсутствующий source quality предварительно нормализуется в `GOOD=0`.

## Транзакция и идемпотентность

Алгоритм записи:

1. Проверить envelope, размер и сигналы по snapshot/cache до транзакции.
2. Начать короткую транзакцию с ограниченными lock и statement timeout.
3. Вставить batch header по `(producerId, producerBatchId)`. При конфликте сравнить `payloadHash`: равный hash немедленно возвращает ранее принятый результат, даже если raw partition уже удалена; несовпадающий даёт `BATCH_ID_REUSED_WITH_DIFFERENT_PAYLOAD`.
4. Для нового batch в стабильном порядке взять shared transaction advisory locks для distinct `signalId`, перепроверить snapshot и зарегистрировать отсутствующие `signal_usage`.
5. Для каждой затронутой UTC-day partition в стабильном порядке получить `pg_try_advisory_xact_lock_shared` из retention barrier и проверить `status = ACTIVE`. Если try-lock недоступен или день уже `RETIRING`, немедленно откатить новый batch и вернуть retryable contention error; блокирующего fallback нет.
6. Batch-insert всех measurement rows и per-machine `recalculation_hint` в той же транзакции, удерживая shared xact locks.
7. Commit. При любой ошибке весь новый batch, включая header и hints, откатывается.

Любая ошибка откатывает весь новый пакет. Partial success отсутствует. Повтор после неопределённого результата использует тот же `producerBatchId`; исправленный пакет получает новый идентификатор.

## Validation

Пакет отклоняется, если:

- размер вне `1..1000`;
- signal отсутствует в допустимом snapshot/cache;
- `value` отсутствует или не совпадает с `TelemetrySignal.valueType`;
- числовое значение равно `NaN` или infinity;
- `observedAt` отсутствует или имеет точность выше поддерживаемых миллисекунд;
- REALTIME event превышает настраиваемый future skew, по умолчанию 5 секунд.

Значение вне `validMin/validMax` сохраняется с `OUT_OF_RANGE`. Источник может передать `GOOD`, `UNCERTAIN` или `BAD`; отсутствие quality означает `GOOD`. Минимальные flags MVP:

```text
OUT_OF_RANGE
CLOCK_SKEW
```

Физическое кодирование: mode `1=REALTIME`, `2=HISTORICAL`; quality `0=GOOD`, `1=UNCERTAIN`, `2=BAD`; flags `1=OUT_OF_RANGE`, `2=CLOCK_SKEW`. Quality не дублируется во flags. Missing measurement выражается отсутствием строки, а не `null`-значением.

## Event time и режимы

Все расчёты используют `observedAt`; порядок `ingest_batch.id` описывает только порядок приёма.

- `REALTIME`: принимает события прошлого и небольшое future clock skew.
- `HISTORICAL`: принимает только прошлый диапазон внутри активного 90-дневного raw window по времени PostgreSQL и требует подготовленные partitions; durable hints создаются вместе с raw, а dirty windows — асинхронно из hints.
- `SCHEDULED`: до времени запуска ничего не записывает; после старта использует обычный realtime protocol.

Late и out-of-order измерения не переписывают raw. Фоновый pipeline объединяет затронутые event-time диапазоны и публикует исправленные проекции отдельно.
