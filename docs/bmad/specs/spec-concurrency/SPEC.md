---
id: SPEC-concurrency
companions:
  - concurrency-rules.md
  - ../../planning-artifacts/architecture/architecture-fkit-bi-2026-10-08/ARCHITECTURE-SPINE.md
  - ../spec-sql-equipment-foundation/SPEC.md
  - ../spec-sql-equipment-foundation/integrity-and-indexes.md
  - ../spec-machine-state-projections/SPEC.md
  - ../spec-raw-telemetry-ingestion/SPEC.md
  - ../spec-generator-domain/SPEC.md
  - ../spec-generator-run-execution/SPEC.md
  - ../spec-transaction-idempotency/SPEC.md
sources: []
---

> **Canonical contract.** Этот SPEC и его companions задают конкурентную работу Analytics и Generator на общей PostgreSQL для MVP.

# Конкурентность сервисов

## Why

Analytics и Generator могут одновременно менять и читать связанные данные, а в будущем могут работать несколькими instances. MVP должен быстро отвечать при contention и сохранять целостность атомарных операций, принимая риск перезаписи устаревшей конфигурации вместо введения версий.

## Capabilities

- **CAP-1**
  - **intent:** Система выполняет конфликтующие пользовательские операции без длительного ожидания и без частичных записей.
  - **success:** При занятом ресурсе команда быстро завершается как конфликт либо целиком фиксируется; длительная очередь HTTP-команд не образуется.

- **CAP-2**
  - **intent:** Несколько Analytics instances безопасно выполняют расчёты разных машин.
  - **success:** На одной Machine в каждый момент публикуется не более одного диапазона, а работы по разным Machine могут идти параллельно; read API возвращает committed projections во время расчёта.

- **CAP-3**
  - **intent:** Несколько Generator instances не создают конфликтующие запуски и могут восстановить выполнение после потери владельца Run.
  - **success:** Резервации машин и historical capacity не дублируются, lease определяет одного владельца выполнения, а просроченный Run становится доступным для явного retry по checkpoint.

## Constraints

- Версии конфигурации и optimistic `row_version` не вводятся; независимые обычные updates используют last-committed-write-wins.
- Целостность каждой команды, FK/unique constraints, packet idempotency и атомарная публикация остаются обязательными; принимаемый риск ограничен потерей параллельного stale edit.
- Координация использует только PostgreSQL, короткие транзакции, scoped row/advisory locks, durable reservations и leases; отдельный distributed lock service не вводится.
- Read API читает committed projections по MVCC и не ожидает длительный replay; очередь workers использует `SKIP LOCKED`, а не глобальную сериализацию.
- Порядок многоресурсных блокировок стабилен; блокировки пользовательских команд ограничены и завершаются быстро при contention.
- Один historical Generator Run одновременно допускается на минимальном demo host; realtime run может работать параллельно в пределах согласованной квоты.

## Non-goals

- Предотвращение потери устаревших полей при одновременных полных `PUT` конфигурации.
- Автоматический takeover и незаметный failover активного Generator Run на другой instance.
- `SERIALIZABLE` isolation для всех операций, глобальные application locks или блокировка всех writes на предприятие.

## Success signal

Тесты с несколькими workers и Generator instances подтверждают отсутствие двойной публикации одного Machine range и пересекающихся reservations; при конфликте команды не ждут долгую блокировку, а committed read API продолжает отвечать.
