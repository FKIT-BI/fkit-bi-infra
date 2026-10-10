---
id: SPEC-machine-state-projections
companions:
  - projection-model.md
  - recalculation-process.md
  - evaluation-deadlines.md
sources: []
---

> **Canonical contract.** Этот SPEC и файлы из `companions:` составляют полный контракт текущей проекции, интервалов и перерасчёта состояния машины.

# Проекции состояния машины

## Why

StateRule evaluator должен публиковать быстро читаемое текущее состояние и корректируемую event-time историю без частичных результатов и без ожидания со стороны frontend. Late data, historical imports и временные deadlines должны актуализировать одни и те же интервалы, сохраняя доступность уже рассчитанной аналитики.

## Capabilities

- **CAP-1**
  - **intent:** Система может предоставить текущее состояние и непрерывную историю машины от момента её активации.
  - **success:** Current state читается одной строкой, а timeline внутри опубликованного coverage содержит ровно одно состояние в каждой точке без дыр и пересечений.

- **CAP-2**
  - **intent:** Система может объединять новые, late и historical данные в удобные диапазоны актуализации.
  - **success:** Dirty windows выравниваются по UTC-минутам, объединяются на машину, получают необходимый левый контекст и пересчитываются до текущего `dataThrough`.

- **CAP-3**
  - **intent:** Система может заменить исторический диапазон без публикации частичного результата.
  - **success:** Перерасчёт готовится и проверяется в staging, а одна короткая транзакция заменяет intervals, current projection и checkpoints; frontend до commit читает старый полный результат.

- **CAP-4**
  - **intent:** Система может выполнить временной переход без поступления нового measurement.
  - **success:** Ближайший stale, activation, release или offline deadline хранится одной строкой на Machine и создаёт переход с `effectiveFrom=deadlineAt` даже при более позднем `detectedAt`.

- **CAP-5**
  - **intent:** Пользователь может асинхронно пересчитать выбранный период или всю историю машины.
  - **success:** `PERIOD` нормализуется и расширяется, `ALL` охватывает `coverageFrom..dataThrough`, job сообщает lifecycle, а результат публикуется атомарно.

- **CAP-6**
  - **intent:** Несколько workers могут безопасно рассчитывать разные машины и восстанавливаться после сбоя.
  - **success:** Per-machine lease исключает конкурентную публикацию одной Machine, `SKIP LOCKED` разрешает параллелизм, а истёкший lease делает незавершённую работу доступной повторно.

## Constraints

- Поля current и interval projections, coverage и API чтения определены в `projection-model.md`.
- Dirty windows, staging publication и user recalculation определены в `recalculation-process.md`.
- PostgreSQL deadline scheduler определён в `evaluation-deadlines.md`.
- `coverageFrom` равен первому переходу Machine в `ACTIVE` и после этого неизменяем.
- Исторический coverage полуоткрытый и имеет UTC-minute-aligned `dataThrough`; точные state transitions сохраняют миллисекундную event-time точность.
- `machine_state_interval` делится только при изменении MachineState и не хранит исторические rule/quality details.
- State intervals не содержат `shiftId`; разделение по сменам выполняют metric buckets.
- Frontend не ожидает перерасчёт и не читает staging.

## Non-goals

- Историческая трассировка matched rule и evaluation quality для каждого state segment.
- Постоянное дерево версий всей timeline.
- Convergence detection для ранней остановки перерасчёта.
- Синхронный recalculation в пользовательском HTTP-запросе.
- Multi-machine recalculation command.
- Retention state intervals и пагинация timeline в этом блоке.

## Success signal

Realtime, deadline или late/historical input даёт непрерывную state timeline от активации машины; во время долгого перерасчёта frontend продолжает читать последнюю полную проекцию, а после короткой публикации видит целиком актуализированный диапазон.
