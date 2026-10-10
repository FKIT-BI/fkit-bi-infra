---
id: SPEC-analytics-modules
companions:
  - module-boundaries.md
sources: []
---

# Модульные границы Analytics и Generator

## Why

MVP совмещает конфигурацию, запись сырой телеметрии, расчёт и чтение аналитики в одном deployment. Явное владение кодом и данными должно удержать этот сервис модульным и оставить понятные seams для последующего разделения.

## Capabilities

- **CAP-1**
  - **intent:** Команда разрабатывает Analytics и Generator как раздельные приложения с внутренними доменными модулями.
  - **success:** Каждый модуль имеет собственную ответственность и узкие application ports; HTTP adapters не вызывают чужие repositories напрямую.
- **CAP-2**
  - **intent:** Фоновые вычисления остаются корректными при повторах и возможном горизонтальном запуске.
  - **success:** Scheduler/worker work и leases имеют durable PostgreSQL представление; при повторе публикация остаётся идемпотентной.

## Constraints

- Analytics и Generator остаются отдельными приложениями, одной PostgreSQL владеет Liquibase Analytics.
- MVP использует package-based modular monolith, а не отдельные build subprojects.
- Утверждённые cross-schema transaction boundaries атомарны в одной PostgreSQL; сетевые вызовы не выполняются внутри них.
- Список модулей, ownership, разрешённые зависимости и transaction seams находятся в `module-boundaries.md`.

## Non-goals

- Внутрисистемный message broker, распределённые транзакции или новая микросервисная платформа.
- Полное физическое извлечение домена Analytics или workers до измеренной потребности.

## Success signal

Команда может собрать и запустить приложения как два deployment units; package rules позволяют тестировать domain/application слой отдельно, а будущий extraction не требует менять публичные API или доменные идентификаторы.
