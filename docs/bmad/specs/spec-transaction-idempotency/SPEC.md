---
id: SPEC-transaction-idempotency
companions:
  - transaction-matrix.md
  - ../../planning-artifacts/architecture/architecture-fkit-bi-2026-10-08/ARCHITECTURE-SPINE.md
  - ../spec-raw-telemetry-ingestion/SPEC.md
  - ../spec-analytics-projection-storage/SPEC.md
  - ../spec-manual-state-overrides/SPEC.md
  - ../spec-generator-run-execution/SPEC.md
  - ../spec-analytics-api-contract/api-conventions.md
sources: []
---

> **Canonical contract.** Этот SPEC и файлы из `companions:` задают транзакционные границы, persistence-подход и восстановление после сбоев для MVP.

# Транзакции и идемпотентность

## Why

Analytics и Generator используют одну PostgreSQL, но независимо принимают команды и фоновую работу. Система должна сохранять целостные изменения при сбоях, не удерживать пользовательские чтения во время долгих расчётов и безопасно повторять незавершённую работу.

## Capabilities

- **CAP-1**
  - **intent:** Команда изменения durable-данных сохраняется целиком либо не оставляет частичного результата.
  - **success:** При проверочном отказе ни одна часть конфигурации, инцидента, ingest batch или связанного durable work не остаётся отдельно зафиксированной.

- **CAP-2**
  - **intent:** Система публикует новый рассчитанный диапазон, не показывая читателям промежуточный результат.
  - **success:** До commit API получает прежнюю полную committed projection, после commit — новую полную projection с соответствующей currency metadata.

- **CAP-3**
  - **intent:** Фоновые расчёты и генерация восстанавливаются после повторной доставки или сбоя процесса.
  - **success:** Повтор завершённого/незавершённого шага не дублирует измерения, интервалы, длительности, количества или buckets.

## Constraints

- Основной persistence API обоих Java-сервисов в MVP — Spring JDBC (`JdbcTemplate`/`NamedParameterJdbcTemplate`); сервисный слой задаёт границы PostgreSQL-транзакций через Spring `@Transactional`.
- Raw ingestion, конфигурация, инциденты, Generator Run, dirty work и публикация аналитики имеют отдельные транзакции; распределённая транзакция между приложениями не используется.
- Длительное чтение raw, replay и формирование/проверка staging не выполняются внутри транзакции замены активных проекций.
- Затронутые доменные изменения и постановка требуемой durable работы коммитятся вместе.
- Читатели используют committed projections; они не читают staging и не ожидают завершения расчёта.
- SQL-запросы параметризованы; пакетные записи применяются для ingestion и массовых операций. PostgreSQL `COPY` допускается только после подтверждения необходимости benchmark-ом.

## Non-goals

- JPA/Hibernate persistence, смешивание ORM и JDBC моделей в MVP.
- Exactly-once обработка каждого отдельного измерения.
- Распределённые транзакции между Analytics, Generator и внешними системами.
- Включение сетевых вызовов, логов или метрик в атомарность PostgreSQL transaction.

## Success signal

Fault-injection проверки показывают, что сбой до commit полностью откатывает соответствующую команду или публикацию; повтор фоновой работы безопасен; при перерасчёте чтение продолжает возвращать последнюю полную версию без чтения raw/staging.

## Решение для повторов ManualIncident

`POST ManualIncident` требует `Idempotency-Key`. Повтор с тем же ключом и тем же каноническим request body возвращает исходный результат создания; тот же ключ с другим body возвращает `409 IDEMPOTENCY_KEY_REUSED`. Запись ключа, hash body и созданного incident атомарна. Ключ ограничен областью пользователя и operation; срок хранения и формат ключа задаются общими API-конвенциями до реализации.
