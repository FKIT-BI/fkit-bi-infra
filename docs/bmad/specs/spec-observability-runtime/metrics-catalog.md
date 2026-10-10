# Каталог метрик

## Правила labels

Labels ограничиваются небольшими справочниками: `service`, `outcome`, `mode`, `job_type`, `projection`, `priority`, `operation`, `exception` с нормализованным ограниченным набором значений. Запрещены `enterpriseId`, `lineId`, `machineId`, `componentId`, `signalId`, `batchId`, `runId`, `incidentId`, URI с реальным ID, текст ошибки и timestamp.

Per-machine диагностика остаётся в business API и structured logs. HTTP metric использует route template, например `/api/v1/machines/{machineId}`, а не фактический URI.

## Стандартные метрики

Оба Java-приложения публикуют стандартные Micrometer series:

- JVM heap/non-heap, GC pauses, threads и process uptime;
- process/system CPU и memory;
- `http.server.requests` по method, templated URI, status и bounded exception;
- Hikari active, idle, pending, max и acquire time;
- executor/task metrics для instrumented bounded pools.

postgres_exporter предоставляет connections, transactions, locks/deadlocks, database size и cache/activity indicators. node_exporter предоставляет CPU, RAM, load и filesystem capacity/free space.

## Analytics custom metrics

| Имя | Тип | Labels | Смысл |
|---|---|---|---|
| `fkit_bi_ingest_batches_total` | counter | `outcome` | Принятые, rejected, duplicate и failed пакеты |
| `fkit_bi_ingest_measurements_total` | counter | `outcome` | Accepted, rejected и dropped measurements |
| `fkit_bi_ingest_batch_size` | histogram | `outcome` | Размеры batch |
| `fkit_bi_ingest_commit_seconds` | histogram | `outcome` | Длительность insert transaction |
| `fkit_bi_producer_sequence_gaps_total` | counter | `mode` | Обнаруженные gaps producer sequence |
| `fkit_bi_dirty_windows` | gauge | `priority`, `status` | Текущий backlog dirty windows |
| `fkit_bi_dirty_oldest_age_seconds` | gauge | `priority` | Возраст старейшего ожидающего window |
| `fkit_bi_projection_lag_seconds` | gauge | `projection` | Lag `current_signal`, `machine_state`, `minute_rollup` |
| `fkit_bi_calculation_jobs_total` | counter | `job_type`, `outcome` | Завершения calculation/recalculation jobs |
| `fkit_bi_calculation_duration_seconds` | histogram | `job_type`, `outcome` | Длительность jobs |
| `fkit_bi_calculation_active` | gauge | `job_type` | Активные jobs |
| `fkit_bi_partition_horizon_days` | gauge | — | Количество заранее доступных future raw partitions |
| `fkit_bi_retention_runs_total` | counter | `outcome` | Запуски partition retention |
| `fkit_bi_incident_mutations_total` | counter | `operation`, `outcome` | CRUD ручных incidents без их ID |

## Generator custom metrics

| Имя | Тип | Labels | Смысл |
|---|---|---|---|
| `fkit_bi_generation_runs_total` | counter | `mode`, `outcome` | Запуски realtime, historical и scheduled generation |
| `fkit_bi_generation_active_runs` | gauge | `mode` | Активные runs |
| `fkit_bi_generation_measurements_total` | counter | `mode`, `outcome` | Generated, written и dropped measurements |
| `fkit_bi_generation_buffer_measurements` | gauge | `mode` | Текущий размер bounded buffer |
| `fkit_bi_generation_write_seconds` | histogram | `mode`, `outcome` | Время записи batch |
| `fkit_bi_generation_schedule_lag_seconds` | gauge | `mode` | Опоздание scheduled/realtime generation относительно плана |

Counter не уменьшается и используется через `rate`/`increase`. Lag, backlog и capacity являются gauges. Histogram buckets настраиваются вокруг SLO, без per-object tag expansion.
