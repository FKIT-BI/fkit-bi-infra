---
id: SPEC-sql-equipment-foundation
companions:
  - schema-model.md
  - integrity-and-indexes.md
  - liquibase-conventions.md
  - ../spec-equipment-core-configuration/configuration-model.md
  - ../spec-equipment-hierarchy/equipment-model.md
  - ../spec-telemetry-signal/signal-model.md
  - ../spec-shift-calendar/shift-rules.md
sources: []
---

> **Canonical contract.** Этот SPEC и файлы из `companions:` задают физический SQL-фундамент конфигурации оборудования и правила Liquibase, обязательные для реализации.

# SQL-фундамент конфигурации оборудования

## Why

Оборудование, телеметрия, аналитика, инциденты и generator используют одну PostgreSQL, поэтому до реализации нужен единый владелец схемы и физические ограничения, не позволяющие разным модулям сохранить противоречивую иерархию. Миграции должны одинаково поднимать пустую базу и безопасно развивать уже используемую схему.

## Capabilities

- **CAP-1**
  - **intent:** Analytics может детерминированно создать логические схемы и конфигурационные таблицы на пустой PostgreSQL.
  - **success:** Liquibase `update` создаёт ожидаемую структуру один раз, а повторный запуск не выполняет changeset повторно и не изменяет данные.

- **CAP-2**
  - **intent:** База данных может отклонять связи между объектами разных владельцев.
  - **success:** Нельзя связать Machine с Line другого Enterprise, а Component или TelemetrySignal — с объектом другой Machine.

- **CAP-3**
  - **intent:** Backend может сохранять Enterprise, ProductionLine, Machine, Component, TelemetrySignal и Shift согласно согласованной доменной модели.
  - **success:** Обязательность, уникальность, типы, локальные диапазоны и разрешённые технические значения защищены SQL-ограничениями, а сложные временные и графовые инварианты проверяются одной доменной транзакцией.

- **CAP-4**
  - **intent:** Система может расширять каталог семантик сигналов и единиц измерения без изменения типа соответствующих колонок.
  - **success:** Неизвестный код отклоняется FK, а новый разрешённый код добавляется отдельным data changeset.

- **CAP-5**
  - **intent:** Analytics и Generator могут использовать общую БД без совместного владения её структурой.
  - **success:** Только Analytics применяет Liquibase; Generator не выполняет DDL и получает доступ лишь к согласованным таблицам и операциям.

## Constraints

- Физические схемы, таблицы и типы определены в `schema-model.md`; ограничения и стартовые индексы — в `integrity-and-indexes.md`.
- Структура changelog, правила changeset, переход с Flyway и роли определены в `liquibase-conventions.md`.
- PostgreSQL разделяется на схемы `equipment`, `telemetry`, `analytics`, `incident` и `generator`; пользовательские доменные таблицы не создаются в `public`.
- PostgreSQL native enum не используется: закрытые технические наборы хранятся как `VARCHAR` или `SMALLINT` с `CHECK`, расширяемые коды — в таблицах-справочниках.
- UUID генерируется backend; timestamps хранятся с миллисекундной точностью в UTC-compatible `TIMESTAMPTZ(3)`.
- Пользовательского физического удаления нет; жизненный цикл конфигурационных сущностей ограничен `ACTIVE` и `DISABLED`.
- Исторические версии конфигурации и optimistic row version не входят в MVP; конкурентные команды используют короткие транзакции и точечные row locks или условные updates.
- Применённый changeset не изменяется; исправление оформляется новым globally unique changeset.

## Non-goals

- Разделение общей PostgreSQL на отдельные физические базы.
- Хранение полной истории изменений конфигурации.
- Реализация бизнес-валидации целиком через triggers и stored procedures.
- Автоматический destructive cleanup старых Flyway metadata или marker table.
- Пользовательское управление справочниками через CRUD API в MVP.

## Success signal

Интеграционный тест поднимает чистую PostgreSQL через Liquibase, сохраняет валидную полную иерархию оборудования и подтверждает, что межвладельческие связи, дубликаты кодов и недопустимые локальные значения отклоняются самой базой; повторный Liquibase `update` проходит без изменений.
