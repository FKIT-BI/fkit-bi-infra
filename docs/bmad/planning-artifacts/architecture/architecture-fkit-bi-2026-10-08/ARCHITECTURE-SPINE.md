---
name: 'FKIT BI data path'
type: architecture-spine
purpose: report
altitude: feature
paradigm: 'Ports and Adapters with single-writer shared-database ownership'
scope: 'PostgreSQL configuration model, raw telemetry, Liquibase and runtime data boundaries'
status: final
created: '2026-10-08'
updated: '2026-10-10'
binds:
  - SPEC-sql-equipment-foundation/CAP-1..CAP-5
  - SPEC-raw-telemetry-ingestion/CAP-1..CAP-6
sources:
  - ../../../specs/spec-sql-equipment-foundation/SPEC.md
  - ../../../specs/spec-raw-telemetry-ingestion/SPEC.md
  - ../../../../architecture/fkit-bi-components.md
  - ../../../specs/spec-mvp-load-slo/SPEC.md
companions:
  - ../../../specs/spec-sql-equipment-foundation/schema-model.md
  - ../../../specs/spec-sql-equipment-foundation/integrity-and-indexes.md
  - ../../../specs/spec-sql-equipment-foundation/liquibase-conventions.md
  - ../../../specs/spec-raw-telemetry-ingestion/telemetry-storage.md
  - ../../../specs/spec-raw-telemetry-ingestion/writer-protocol.md
  - ../../../specs/spec-raw-telemetry-ingestion/availability-policy.md
---

# Architecture Spine — FKIT BI data path

## Design Paradigm

Каждое Spring-приложение использует Ports and Adapters: domain/application не зависит от JDBC и HTTP. Общая PostgreSQL является интеграционной границей с единственным DDL-владельцем; готовые аналитические проекции отделяют горячую запись raw от frontend-чтения.

```mermaid
flowchart LR
    WEB[Web] --> AAPI[Analytics HTTP adapter]
    WEB --> GAPI[Generator HTTP adapter]
    AAPI --> ADOM[Analytics application/domain]
    GAPI --> GDOM[Generator application/domain]
    ADOM --> ADB[Analytics repositories]
    GDOM --> GDB[Generator repositories and TelemetrySink]
    ADB --> PG[(PostgreSQL)]
    GDB --> PG
    LIQ[Analytics Liquibase] --> PG
```

## Invariants & Rules

### AD-1 — [ADOPTED] Одна PostgreSQL с логическими schemas

- **Binds:** Все хранимые домены MVP.
- **Prevents:** Отдельные модули создают конфликтующие таблицы в `public` или преждевременно требуют распределённых транзакций.
- **Rule:** Доменные таблицы располагаются в логических схемах `equipment`, `telemetry`, `analytics`, `incident`, `generator` или `identity`; учётные записи принадлежат `identity`, миграции всех схем выполняет только Analytics, а MVP использует одну физическую PostgreSQL.

### AD-2 — [ADOPTED] Единственный владелец DDL

- **Binds:** Liquibase и запуск Analytics/Generator.
- **Prevents:** Конкурирующие миграции и запуск Generator против неполной схемы.
- **Rule:** Только Analytics применяет Liquibase при startup; его readiness остаётся false до успеха, а Generator стартует после Analytics readiness. В тестовом контуре оба приложения, встроенный Liquibase и exporter используют один общий PostgreSQL account; отдельные owner/runtime credentials и DB roles отложены. Оба приложения дополнительно проверяют точное поддерживаемое значение `equipment.schema_release`; production-разделение credentials не входит в MVP.

### AD-3 — [ADOPTED] Владение данными по модулям

- **Binds:** Equipment, telemetry, projections, incidents и generator state.
- **Prevents:** Два сервиса независимо изменяют одну бизнес-сущность.
- **Rule:** Analytics изменяет `equipment`, `analytics` и `incident`; Generator изменяет `generator` и только добавляет rows через telemetry append contract; междоменные исключения фиксируются grants и интеграционными тестами.

### AD-4 — [ADOPTED] Нормализованное ядро оборудования

- **Binds:** Enterprise, ProductionLine, Machine, Component, TelemetrySignal, Shift и справочники.
- **Prevents:** Дублирование владельцев и противоречивые межпредметные ссылки.
- **Rule:** Владение моделируется FK и составными FK на границах Enterprise/Machine; расширяемые semantic/unit codes являются справочниками; JSONB разрешён только для валидированных display parameters, которые не участвуют в фильтрах и расчётах. Component tree mutations сериализуются lock владельца Machine, Shift schedule mutations — lock Enterprise, а первое использование Signal и изменение его семантики используют shared/exclusive transaction advisory locks, производные от `signal_id`. Возможная коллизия ключа только избыточно сериализует разные Signal и не нарушает целостность.

### AD-5 — [ADOPTED] Append-only raw hot path

- **Binds:** `telemetry.ingest_batch` и `telemetry.raw_measurement`.
- **Prevents:** FK/UPSERT/index amplification блокирует или замедляет ingestion.
- **Rule:** Raw measurement не обновляется, не имеет per-row FK или unique и содержит ровно одно типизированное значение; валидность Signal проверяется до транзакции по snapshot/cache. Транзакция raw также фиксирует durable `signal_usage` при первом use и per-machine `recalculation_hint`; оба служебных набора переживают удаление raw.

### AD-6 — [ADOPTED] Идемпотентность на уровне batch

- **Binds:** TelemetrySink retry и historical checkpoints.
- **Prevents:** Неопределённый результат commit создаёт повторные measurements.
- **Rule:** Пакет из 1..1000 rows фиксируется одной короткой транзакцией; `(producer_id, producer_batch_id)` уникален и связан с SHA-256 точного versioned binary encoding `TELEMETRY_BATCH_V1`. Равный hash означает idempotent success, несовпадающий — `BATCH_ID_REUSED_WITH_DIFFERENT_PAYLOAD`.

### AD-7 — [ADOPTED] Event-time partitioning и retention

- **Binds:** Raw storage lifecycle.
- **Prevents:** Построчная очистка и неограниченный рост горячей таблицы.
- **Rule:** `raw_measurement` разделяется на UTC-day RANGE partitions по `observed_at`, без default partition, с локальным индексом `(signal_id, observed_at)`; raw retention составляет 90 суток по времени PostgreSQL. Historical принимает только этот active window. Приём raw берёт shared try-lock для UTC-дня и в той же транзакции фиксирует raw и durable hint; если lock недоступен из-за retention, пакет получает retryable отказ без ожидания (далее действует политика ограниченного retry/потери для telemetry). Worker удерживает shared session lock на всё время raw-read и publication; если lock недоступен, не начинает работу. Retention берёт exclusive try-lock и повторно проверяет hints, jobs/leases и неполностью опубликованные проекции. Любое DDL ограничено коротким `lock_timeout`; при конфликте операция отменяется и повторяется позднее. Read API читает только projections и не берёт retention lock.

### AD-8 — [ADOPTED] Независимые write, calculation и read paths

- **Binds:** Ingestion, workers и Analytics read API.
- **Prevents:** Frontend ждёт вставку или перерасчёт, а worker блокирует raw writer.
- **Rule:** Ingestion только добавляет raw; workers читают committed raw без row locks и публикуют новые проекции отдельной короткой транзакцией; API читает только последнюю committed projection и её freshness metadata.

### AD-9 — [ADOPTED] Ограниченный ресурсный профиль

- **Binds:** Pools, batches, worker concurrency и benchmark.
- **Prevents:** Historical generation вытесняет realtime и query workload на минимальном стенде.
- **Rule:** Базовый профиль — 30 measurements/s, benchmark — 200/s на 30 минут, 1000/s на 60 секунд и 1000–2000/s throttled historical; Analytics использует один pool до 14–16 connections и semaphore limits, не позволяющие workers занять весь pool, Generator — 2–3 connections, batch — не более 1000 rows. Historical проходит storage preflight и останавливается при disk pressure.

### AD-10 — [ADOPTED] Partition DDL вне горячей транзакции

- **Binds:** Создание и удаление partitions.
- **Prevents:** Insert ждёт DDL-lock или создаёт таблицу на demand.
- **Rule:** Liquibase устанавливает `SECURITY DEFINER` routines с fixed `search_path`, validated date и единым topology advisory lock. Analytics заранее поддерживает диапазон raw window плюс 7 future days; create и detach/drop используют короткие lock/statement timeouts и retry. Если DDL не может получить блокировки сразу, оно отменяется и повторяется вне горячего пути; ingest не выполняет DDL. `DETACH CONCURRENTLY` отложен.

### AD-11 — [ADOPTED] Единая DB-учётная запись тестового контура

- **Binds:** Liquibase, runtime services и monitoring.
- **Prevents:** Настройка тестового стенда разрастается отдельными учетными записями и секретами до появления практической необходимости.
- **Rule:** В тестовом контуре один общий PostgreSQL account используется Analytics, Generator, Liquibase и postgres_exporter. Это сознательный MVP-компромисс, не production security baseline. Сохраняются application-level владение доменными данными, readiness и проверка `equipment.schema_release`; ролевое разделение возвращается перед production/реальными внешними данными.

### AD-12 — [ADOPTED] Единое физическое кодирование telemetry

- **Binds:** Generator writer, Analytics reader и SQL CHECK constraints.
- **Prevents:** Сервисы по-разному интерпретируют одинаковые `SMALLINT` и flag bits.
- **Rule:** Batch mode: `1=REALTIME`, `2=HISTORICAL`; source quality: `0=GOOD`, `1=UNCERTAIN`, `2=BAD`; validation flags: `1=OUT_OF_RANGE`, `2=CLOCK_SKEW`. Quality не дублируется в flags; producer IDs ограничены 128 символами, `value_text` — 500.

### AD-13 — [ADOPTED] Доступ по IP и домену с явным TLS-режимом

- **Binds:** Входной HTTP(S) и развёртывание MVP на Dev.
- **Prevents:** Ожидание, что wildcard-сертификат автоматически удостоверяет IP, или незаметное понижение TLS при ошибке выпуска.
- **Rule:** Nginx принимает запросы по IP и доменному имени. В MVP нужен один host `bi.kitexp.ru`; Analytics и Generator маршрутизируются через path-based `/api/analytics/` и `/api/generator/`, отдельные DNS subdomains не требуются. Единственная application A-запись `bi.kitexp.ru` указывает на `45.132.176.28`; wildcard A-запись не нужна. Сертификат содержит `bi.kitexp.ru` и `*.bi.kitexp.ru`; wildcard validation выполняется Certbot DNS-01 через временную TXT-запись `_acme-challenge.bi.kitexp.ru`, автоматически созданную auth/cleanup hooks в Yandex Cloud DNS API. IP endpoint `http://45.132.176.28` остаётся доступен по HTTP; HTTPS по IP сейчас не требуется. `TLS_MODE=public|self-signed` выбирается явно; self-signed сертификат генерируется автоматически для dev/demo, а сбой public issuance не переключает режим молча. DNS credentials — deploy secret с минимальным доступом к целевой зоне.

### AD-14 — [ADOPTED] Три ежедневных полных DB dump

- **Binds:** Восстановление demo MVP.
- **Prevents:** Неясность состава копии и накопление неограниченного числа локальных dump.
- **Rule:** Один раз в день создаётся полный PostgreSQL custom-format logical dump базы приложения; хранятся только три последние ежедневные копии с ограниченными файловыми правами. Dump включает схему и данные application DB, включая конфигурацию, raw в текущем retention, проекции, инциденты, сценарии/запуски и Liquibase metadata. Он не заменяет копирование ролей, deployment secrets, TLS keys или Prometheus/Grafana volumes; это тестовый контурный recovery, не защита от потери хоста.

### AD-15 — [ADOPTED] Неблокирующий retention maintenance

- **Binds:** Удаление raw UTC-day partitions при активных запросах и пересчётах.
- **Prevents:** Ожидание очистки со стороны ingestion, аналитического чтения или пользовательских запросов.
- **Rule:** Maintenance пытается получить exclusive per-day lock без ожидания, затем перепроверяет долговечные hints, jobs/leases и незавершённые публикации. Raw insert берёт shared try-lock в транзакции с записью durable hint; worker удерживает shared lock на всё время чтения raw и публикации результата. Вставка не ждёт: при конфликте получает retryable отказ и следует bounded retry/явной telemetry loss policy. Read API работает по projections и не берёт этот lock. Partition DDL имеет короткий `lock_timeout`, поэтому обслуживание может быть отложено из-за активной транзакции, а запросы frontend не затрагиваются.

## Consistency Conventions

| Concern | Convention |
| --- | --- |
| Naming | SQL `snake_case`; stable API codes; UTC-day partition name `raw_measurement_YYYYMMDD` |
| Data & formats | UUID назначает backend; event/audit time — `TIMESTAMPTZ(3)`; local Shift time — `TIME(0)` + `DATE` |
| Mutation | Конфигурация — транзакционный CRUD без physical delete; raw — append-only; projections — replace/publish |
| Migration | Explicit Liquibase includes; YAML orchestration + formatted SQL; applied changesets immutable |
| Availability | Bounded retry/buffers; telemetry loss допустима и наблюдаема; query path сохраняет connection reserve |

## Stack

| Name | Version |
| --- | --- |
| Java | 21 |
| Spring Boot | 3.5.16 |
| Liquibase Community | 4.31.1 (Spring Boot 3.5.16 managed) |
| PostgreSQL | 16 |
| PostgreSQL JDBC | 42.7.11 (Spring Boot 3.5.16 managed) |

## Structural Seed

```text
fkit-bi-analytics/src/main/resources/db/changelog/
  db.changelog-master.yaml
  releases/
    001-foundation/
    002-equipment/
    003-telemetry/
    004-analytics/
    005-incidents/
    006-generator/
```

## Capability → Architecture Map

| Capability / Area | Lives in | Governed by |
| --- | --- | --- |
| Конфигурация оборудования | Analytics equipment module + `equipment` | AD-1, AD-3, AD-4 |
| Liquibase bootstrap | Analytics migration adapter | AD-2, AD-10, AD-11 |
| Realtime/historical ingestion | Generator TelemetrySink + `telemetry` | AD-5, AD-6, AD-7, AD-9, AD-12 |
| Расчёт проекций | Analytics calculation workers + `analytics` | AD-8, AD-9 |
| Frontend read API | Analytics query module | AD-8 |
| Retention | Analytics maintenance worker | AD-7, AD-10, AD-11 |

## Deferred

- Механизм будущего физического разделения БД — возвращаться только при выделении ingestion/calculation в отдельный deployment.
- Kafka/ETL adapter — возвращаться при появлении внешних производителей или требовании durable buffering вне PostgreSQL.
- Набор дополнительных raw indexes — добавлять только после зафиксированного slow query и `EXPLAIN (ANALYZE, BUFFERS)`.
- Масштабирование более одного экземпляра Analytics — детализировать перед horizontal deployment; MVP использует один экземпляр.
- `DETACH PARTITION CONCURRENTLY` и отдельный maintenance process — возвращаться только если короткий ordinary detach с timeout не проходит benchmark.
- Отдельные datasource pools по workload class — вводить только если один pool с semaphore limits не сохраняет query SLO.
