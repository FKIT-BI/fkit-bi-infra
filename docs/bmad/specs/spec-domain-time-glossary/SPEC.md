---
id: SPEC-domain-time-glossary
companions:
  - domain-glossary.md
  - ../spec-shift-calendar/shift-rules.md
  - ../spec-sql-equipment-foundation/schema-model.md
  - ../spec-analytics-api-contract/api-conventions.md
sources: []
---

# Единый язык домена и времени

## Why

Конфигурация, телеметрия, расчёт состояний, смены и API используют единую производственную временную шкалу. Общий глоссарий исключает расхождения event time, локальных дат и границ интервалов.

## Capabilities

- **CAP-1**
  - **intent:** Все модули одинаково трактуют временные значения и производственные сущности.
  - **success:** SQL, Java и OpenAPI используют согласованные timestamp, duration, shift occurrence и projection-watermark semantics.

## Constraints

- Абсолютное время хранится с точностью до миллисекунды и переносится через ISO-8601 date-time; предприятие задаёт IANA timezone для локального календаря смен.
- Временные диапазоны полуоткрытые `[from,to)`; точные определения терминов находятся в `domain-glossary.md`.
- DST, применимость смен и ShiftOccurrence определяются `shift-rules.md`, не локальной логикой отдельных API.

## Non-goals

- Сохранение локального времени как самостоятельного event timestamp.
- Ежедневные материализованные строки календаря смен.
- Отдельные системные identifiers для day/night/all shifts.

## Success signal

Measurements, состояния и агрегаты на границе смены относятся к одному и тому же `shiftId + shiftDate` при realtime и historical replay; повтор расчёта воспроизводит те же UTC boundaries.
