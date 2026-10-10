# Архитектурная валидация SQL и telemetry

Дата: 2026-10-09  
Область: configuration SQL, raw telemetry, Liquibase, partition lifecycle, runtime DB boundaries.  
Вердикт: **PASS WITH IMPLEMENTATION CONDITIONS, без смены базовой архитектуры**.

## Итог

Одна PostgreSQL, нормализованное equipment-ядро, типизированная append-only raw telemetry, суточные UTC-партиции и чтение готовых проекций подходят для функционального MVP. Java/PostgreSQL справятся с согласованной номинальной нагрузкой; отдельная TSDB, Kafka или вторая база сейчас не нужны.

Первоначальные замечания reviewer gate закрыты уточнениями в spine и связанных specs. Остались обычные PostgreSQL integration checks и нагрузочный benchmark на этапе реализации.

## Что уже спроектировано правильно

- `Machine.enterprise_id` не является ошибочной денормализацией: он нужен свободной Machine, а составной FK гарантирует согласованность назначенной Line.
- `Component.machine_id + parent_component_id` и `TelemetrySignal.machine_id + component_id` правильно используют составные FK для same-owner integrity.
- `Machine.parameters` и `Component.parameters` допустимо хранить JSONB: они ограничены, предназначены только для отображения и не участвуют в поиске или расчётах.
- Batch header отделён от measurements корректно; типизированные `value_*` лучше JSONB для hot path.
- Отсутствие per-measurement FK/unique допустимо как осознанная оптимизация при атомарном batch writer и интеграционных проверках.
- UTC-day `RANGE(observed_at)` и `(signal_id, observed_at)` соответствуют retention и расчётным запросам.
- PostgreSQL MVCC позволяет обычному `SELECT` не блокировать `INSERT`; frontend должен читать проекции, а не raw.

## Обязательные исправления

### 1. Partition maintenance

Analytics runtime не получает owner credentials. Liquibase создаёт узкие owner-owned routines; Analytics получает только `EXECUTE`.

- create: standalone child table → UTC `CHECK` → локальный индекс → `ATTACH PARTITION`;
- общий advisory lock на изменение topology;
- `lock_timeout` и `statement_timeout` ограничены;
- retention: обычный detach с очень коротким lock timeout и retry для простого MVP;
- `DETACH ... CONCURRENTLY` отложен до отдельного autocommit maintenance job;
- отсутствие нужной future partition делает readiness false заранее, а не создаёт DDL в insert transaction.

### 2. Content-bound idempotency

В `ingest_batch` добавляется `payload_hash BYTEA NOT NULL`. SHA-256 считается по единому каноническому binary contract. Duplicate key с тем же hash — успех, с другим — `BATCH_ID_REUSED_WITH_DIFFERENT_PAYLOAD`.

### 3. Durable handoff в аналитику

Raw batch и `telemetry.recalculation_hint` по затронутым Machine/range фиксируются одной транзакцией. Worker идемпотентно объединяет hints в dirty ranges. Post-commit callback без durable row недостаточен.

### 4. Historical и retention

- Historical Run принимает только event time внутри активного 90-дневного raw window.
- Граница вычисляется по времени PostgreSQL и UTC-day; удаляются только полностью истёкшие сутки.
- Retention запрещён при unconsumed hint, queued/running/retryable recalculation, worker lease или неполностью опубликованной проекции.
- Failed job остаётся retention-blocking до явного решения.

### 5. Неисчезающий факт первого использования

Добавляется `telemetry.signal_usage(signal_id PK, first_observed_at)`, не удаляемая вместе с raw. При первом measurement writer и изменение смысловых полей Signal используют общий сериализующий протокол. Это не позволяет после retention переопределить смысл исторического `signal_id`.

### 6. Aggregate concurrency

- изменение дерева Component сериализуется lock владельца Machine до recursive cycle check;
- изменение Shift schedule сериализуется lock владельца Enterprise до проверки пересечений;
- порядок locks одинаков во всех командах.

### 7. Однозначное физическое кодирование

Предлагаемая нормативная карта:

```text
batch mode:       1=REALTIME, 2=HISTORICAL
source quality:   0=GOOD, 1=UNCERTAIN, 2=BAD
validation flags: 1=OUT_OF_RANGE, 2=CLOCK_SKEW
```

`SOURCE_UNCERTAIN` и `SOURCE_BAD` удаляются из flags: они дублируют `source_quality` и допускают противоречивую строку.

### 8. Bounded hot-path fields и header cleanup

- `producer_id VARCHAR(128)`;
- `producer_batch_id VARCHAR(128)`;
- `value_text VARCHAR(500)`;
- все timestamps — `TIMESTAMPTZ(3)`;
- `ingest_batch` удаляется bounded chunks только после истечения idempotency/retention horizon и удаления соответствующего raw;
- cleanup получает отдельный индекс и monitoring dead tuples/vacuum.

### 9. Реальные bulkheads

Общий connection limit недостаточен. Query сохраняет недоступный workers резерв; ingestion, calculation, recalculation, maintenance и historical ограничиваются отдельными pools или semaphores и bounded acquisition timeout.

`200 measurements/s` означает 30-минутный benchmark, а не 90-дневную sizing-гарантию. При номинальных 30/s за 90 суток образуется около 233 млн raw rows. 100 GB остаётся проверяемой нижней границей; перед Historical Run выполняется storage preflight, при <20% free historical приостанавливается/отклоняется.

### 10. Migration/startup lifecycle

1. Остановить writers при schema-changing deployment.
2. Запустить one-shot Liquibase из Analytics artifact с `fkit_bi_owner`.
3. Запустить Analytics только с `fkit_bi_analytics`.
4. Analytics readiness проверяет schema release, seeds и partition horizon.
5. Generator с `fkit_bi_generator` стартует после readiness и отдельно проверяет совместимую schema release.

Текущий Compose с одним `${POSTGRES_USER}` и зависимостью обоих сервисов только от PostgreSQL этому контракту не соответствует и должен быть изменён при реализации.

## Полезные, но не блокирующие поправки

- Выровнять SQL `timezone VARCHAR(100)` с OpenAPI `maxLength: 100`.
- Обновить оба Java-сервиса с Spring Boot 3.5.0 до одного проверенного актуального patch ветки 3.5; Liquibase и JDBC оставить под BOM.
- Для release/benchmark фиксировать container image digest; major-floating tags оставить только local development.
- Сохранить отсутствие raw PK/FK, но добавить offline consistency diagnostic для orphan batches, count/min/max и ordinal duplication.
- Отдельный Shift validity index добавлять только после измеренного query plan.

## Решение reviewer gate

Архитектуру следует **сохранить**. Обязательные уточнения внесены в spine и связанные specs; повторный lint проходит без findings. Повторная adversarial-проверка, проверка целостности и проверка реализуемости дали PASS WITH CLARIFICATIONS / IMPLEMENTATION CONDITIONS. SQL/raw блок согласован для реализации; PostgreSQL integration checks и нагрузочный benchmark выполняются при реализации. Следующий блок — физическая модель аналитических проекций.

## Полные независимые проверки

- [Нормализация и integrity](reviews/review-normalization.md)
- [Актуальность и brownfield reality](reviews/review-currentness.md)
- [Adversarial concurrency/operations](reviews/review-adversarial.md)
- [Повторная adversarial-проверка](reviews/recheck-adversarial.md)
- [Повторная проверка целостности](reviews/recheck-integrity.md)
- [Повторная проверка реализуемости](reviews/recheck-reality.md)

## Первичные технические источники

- [PostgreSQL 16 declarative partitioning](https://www.postgresql.org/docs/16/ddl-partitioning.html)
- [PostgreSQL 16 ALTER TABLE / DETACH PARTITION](https://www.postgresql.org/docs/16/sql-altertable.html)
- [PostgreSQL 16 MVCC](https://www.postgresql.org/docs/16/mvcc-intro.html)
- [Spring Boot 3.5 system requirements](https://docs.spring.io/spring-boot/3.5/system-requirements.html)
- [Spring Boot common Liquibase properties](https://docs.spring.io/spring-boot/3.5/appendix/application-properties/index.html)
