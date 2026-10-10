# Хранение raw telemetry

## Логические таблицы

MVP использует batch header и отдельные типизированные строки:

```text
telemetry.ingest_batch
telemetry.raw_measurement
telemetry.signal_usage
telemetry.recalculation_hint
telemetry.raw_partition_registry
```

`ingest_batch` не партиционируется на первом этапе и хранит:

| Поле | Тип | Правило |
| --- | --- | --- |
| `id` | `BIGINT` | Монотонный идентификатор из cached sequence |
| `producer_id` | `VARCHAR(128)` | Стабильный идентификатор writer |
| `producer_batch_id` | `VARCHAR(128)` | Идемпотентный идентификатор пакета у producer |
| `producer_sequence` | `BIGINT` | Возрастающий номер для обнаружения gaps |
| `payload_hash` | `BYTEA` | SHA-256 канонического содержимого пакета |
| `generator_run_id` | `UUID NULL` | Источник generator snapshot, без обязательного FK |
| `mode` | `SMALLINT` | `1=REALTIME`, `2=HISTORICAL` |
| `received_at` | `TIMESTAMPTZ(3)` | Время записи, назначенное PostgreSQL |
| `measurement_count` | `INTEGER` | Число строк пакета |
| `min_observed_at` | `TIMESTAMPTZ(3)` | Минимальный event time пакета |
| `max_observed_at` | `TIMESTAMPTZ(3)` | Максимальный event time пакета |

Уникальность `(producer_id, producer_batch_id)` обеспечивает идемпотентность пакета. `producer_sequence` диагностирует пропуски, но пропуск не блокирует следующий пакет.

`raw_measurement` хранит:

| Поле | Тип | Правило |
| --- | --- | --- |
| `ingest_batch_id` | `BIGINT` | Batch header |
| `ordinal` | `INTEGER` | Позиция внутри пакета `0..999` |
| `signal_id` | `UUID` | Ссылка по значению без физического FK |
| `observed_at` | `TIMESTAMPTZ(3)` | Event time с миллисекундной точностью |
| `value_double` | `DOUBLE PRECISION NULL` | Значение `DOUBLE` |
| `value_long` | `BIGINT NULL` | Значение `LONG` |
| `value_boolean` | `BOOLEAN NULL` | Значение `BOOLEAN` |
| `value_text` | `VARCHAR(500) NULL` | Значение `STRING` |
| `source_quality` | `SMALLINT` | `0=GOOD`, `1=UNCERTAIN`, `2=BAD` |
| `validation_flags` | `INTEGER` | Битовая маска диагностических признаков |

Ровно одна `value_*` колонка заполнена. Логический `receivedAt` измерения читается из batch header и не дублируется в каждой строке.

`signal_usage` имеет одну неистекающую строку на использованный Signal:

```text
signal_id UUID PRIMARY KEY REFERENCES equipment.telemetry_signal(id)
first_observed_at TIMESTAMPTZ(3) NOT NULL
first_received_at TIMESTAMPTZ(3) NOT NULL
```

Она сохраняет необратимый факт первого raw после удаления суточных partitions. Writer в стабильном порядке берёт shared transaction advisory lock, производный от каждого `signal_id`, сверяет snapshot с текущей семантикой и выполняет `INSERT ... ON CONFLICT DO NOTHING`. Изменение смысловых полей Signal берёт соответствующий exclusive transaction advisory lock и допускается только при отсутствии `signal_usage`. Advisory key детерминированно извлекается общей функцией из UUID; коллизия лишь сериализует две независимые операции и не ослабляет проверку.

`recalculation_hint` сохраняется в той же транзакции, что header и raw, по одной строке на затронутую Machine:

```text
id BIGINT
ingest_batch_id BIGINT
machine_id UUID
from_observed_at TIMESTAMPTZ(3)
to_observed_at TIMESTAMPTZ(3)  // exclusive
created_at TIMESTAMPTZ(3)
consumed_at TIMESTAMPTZ(3) NULL
```

Analytics идемпотентно объединяет hints в minute-aligned dirty ranges. Потеряемый post-commit callback не используется.

`raw_partition_registry` координирует lifecycle каждой UTC-day partition:

```text
partition_day DATE PRIMARY KEY
status VARCHAR(16)  // ACTIVE | RETIRING
created_at TIMESTAMPTZ(3)
retiring_at TIMESTAMPTZ(3) NULL
```

Для каждого UTC-дня применяется единый per-day advisory-lock barrier. Ingest и создание пользовательского задания используют `pg_try_advisory_xact_lock_shared` и проверяют `ACTIVE`; raw + durable hint фиксируются одной транзакцией. Если shared try-lock недоступен, операция немедленно возвращает retryable результат — блокирующего ожидания нет. Worker получает session-level shared lock до чтения raw и удерживает его до commit publication; при недоступности lock оставляет job в очереди. Recovery после падения процесса освобождает session lock автоматически, а durable job/lease остаётся видим maintenance.

Retention получает exclusive per-day `pg_try_advisory_xact_lock`; при конфликте пропускает день и повторяет позже. Под lock переводит registry row в `RETIRING`, повторно проверяет hints, пересекающиеся jobs/leases и незавершённую публикацию, затем выполняет detach/drop. При отказе или ошибке DDL статус возвращается в `ACTIVE`; после успешного удаления partition registry row удаляется. Все создания raw/hint/job обязаны участвовать в этом протоколе. Partition DDL имеет короткие `lock_timeout`/`statement_timeout`: конфликт активной SQL-транзакции отменяет maintenance и переносит его на повтор, а не заставляет его ждать.

## Горячий write path

`raw_measurement` является append-only таблицей без:

- `UPDATE` и per-row `UPSERT`;
- физических FK на `TelemetrySignal` и `ingest_batch`;
- уникального ключа отдельного измерения;
- индексов по значениям и quality;
- `JSONB` payload.

Пакетная идемпотентность предотвращает повтор всей транзакции. Повторная отправка тех же значений под новым `producerBatchId` считается новым пакетом; exactly-once на уровне measurement не предоставляется.

`ingest_batch` остаётся непартиционированным. После истечения idempotency horizon и удаления соответствующего raw старые headers удаляются небольшими chunks по индексу `(max_observed_at, id)`; dead tuples и vacuum lag наблюдаются метриками.

## Партиционирование

`raw_measurement` партиционируется `RANGE (observed_at)` по UTC-суткам. Нужные partitions активного 90-дневного окна и семь суток вперёд создаются до запуска writer; DDL отсутствует в транзакции вставки.

Основной индекс каждой partition:

```text
(signal_id, observed_at)
```

Дополнительные индексы вводятся только после измеренного query plan. Обычный frontend не читает raw; диагностическая выборка всегда ограничена `signalId`, `from`, `to` и максимальным числом точек.

Liquibase устанавливает partition routines с фиксированным `search_path`, проверкой date range и общим topology advisory lock. Analytics вызывает create/detach с короткими `lock_timeout`/`statement_timeout` и bounded retry. MVP использует обычный detach: если DDL lock нельзя получить в заданный короткий timeout, транзакция отменяется и retention откладывается; `DETACH CONCURRENTLY` и отдельный maintenance process не вводятся.

Raw хранится 90 суток по времени PostgreSQL. Удаляется только полностью истёкшая UTC-day partition в `RETIRING` и только если нет unconsumed hint, queued/running/retryable dirty или full-recalculation job, worker lease и неопубликованной зависимой проекции. Failed job остаётся retention-blocking до явного решения. Read API обслуживается из projections и не участвует в lock barrier; запросы, непосредственно читающие raw, могут кратко конфликтовать с обычным detach, поэтому DDL ограничен `lock_timeout` и будет отложен при таком конфликте. Построчное удаление raw не используется. После удаления partition полный перерасчёт диапазона невозможен, но уже опубликованная аналитика продолжает читаться.
