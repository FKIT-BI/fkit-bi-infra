---
id: SPEC-analytics-projection-storage
companions:
  - projection-storage.md
  - ../../planning-artifacts/architecture/architecture-fkit-bi-2026-10-08/ARCHITECTURE-SPINE.md
  - ../spec-sql-equipment-foundation/schema-model.md
  - ../spec-sql-equipment-foundation/integrity-and-indexes.md
  - ../spec-raw-telemetry-ingestion/telemetry-storage.md
  - ../spec-raw-telemetry-ingestion/writer-protocol.md
  - ../spec-signal-quality-freshness/current-projection.md
  - ../spec-signal-quality-freshness/freshness-rules.md
  - ../spec-machine-state-projections/projection-model.md
  - ../spec-machine-state-projections/recalculation-process.md
  - ../spec-machine-state-projections/evaluation-deadlines.md
  - ../spec-machine-state-catalog/state-catalog.md
  - ../spec-minute-rollups/rollup-model.md
  - ../spec-minute-rollups/calculation-rules.md
  - ../spec-manual-state-overrides/effective-timeline.md
  - ../spec-loss-reasons-incidents/attribution-and-lifecycle.md
  - ../spec-loss-reasons-incidents/loss-reason-model.md
  - ../spec-analytics-api-contract/api-conventions.md
  - ../spec-analytics-api-contract/dto-contract.md
  - ../spec-mvp-load-slo/load-profile.md
sources: []
---

> **Canonical contract.** Этот SPEC и файлы в `companions:` задают физическое хранение аналитических проекций для MVP.

# Физическое хранение аналитических проекций

## Why

Frontend должен быстро читать current-состояние, временные линии и исторические показатели, пока ingestion и фоновые пересчёты продолжают работать. Физическая модель связывает уже согласованные правила расчёта с компактными таблицами и понятной границей публикации.

## Capabilities

- **CAP-1**
  - **intent:** Система предоставляет актуальные значения сигналов и состояние машины из готовых проекций.
  - **success:** Current-запрос использует индексированные строки Signal и Machine, не читает raw telemetry и возвращает currency metadata.

- **CAP-2**
  - **intent:** Система предоставляет calculated/effective timelines и исторические показатели по ограниченному периоду.
  - **success:** Запросы читают interval и минутные проекции по Machine/Signal и времени; line/enterprise показатели агрегируют машинные факты.

- **CAP-3**
  - **intent:** Система публикует пересчитанную аналитику без частичного результата для читателя.
  - **success:** Пока вычисление готовится, API видит прежнюю committed проекцию; новая версия становится видна целиком после короткой публикационной транзакции.

## Constraints

- Нормативные таблицы, ключи, индексы, staging и публикационный протокол находятся в `projection-storage.md`.
- Raw telemetry остаётся append-only и не заменяется аналитическими проекциями.
- Физически хранятся только согласованные current, interval и минутные проекции; отдельные 1h/1d и line/enterprise агрегаты в MVP отсутствуют.
- Аналитические таблицы не партиционируются и хранятся весь срок demo-данных.
- Read API использует committed projections, не читает staging и не ждёт worker.

## Non-goals

- Нормативная семантика state, формул, shift calendar, incidents и resolution: она описана в соседних спецификациях.
- Автоматическое удаление аналитической истории и архивация demo-данных.
- Дополнительные проекции, вводимые без подтверждённого query shape или benchmark.

## Assumptions

- Staging хранится в обычных durable таблицах по `dirty_range_id`, чтобы продолжить либо безопасно повторить расчёт после сбоя.

## Success signal

Current, timeline, shift, loss и metric запросы обслуживаются подготовленными индексированными данными. При поздней telemetry, изменении ручного инцидента или перерасчёте frontend продолжает видеть последний полный результат и получает новую согласованную версию после commit.
