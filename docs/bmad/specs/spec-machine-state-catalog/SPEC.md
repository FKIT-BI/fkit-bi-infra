---
id: SPEC-machine-state-catalog
companions:
  - state-catalog.md
  - duration-classification.md
sources: []
---

> **Canonical contract.** Этот SPEC и файлы из `companions:` составляют полный контракт бизнес-семантики MachineState и классификации времени.

# Каталог состояний машины

## Why

Одинаковые state intervals должны одинаково влиять на dashboard, хронометраж, Availability, Performance и data quality. Без нормативного смысла `IDLE`, `SETUP`, `PLANNED_STOP` и `OFFLINE` разные API могут считать один период несовместимыми способами.

## Capabilities

- **CAP-1**
  - **intent:** Система может однозначно классифицировать каждый effective MachineState.
  - **success:** Для каждого state определены operating/productive/planned/loss/data-gap semantics, одинаковые для current, timeline и aggregates.

- **CAP-2**
  - **intent:** Analytics может построить аддитивные длительности для Availability и Performance.
  - **success:** State durations раскладываются без double count в planned production, operating и productive time, а проценты вычисляются из сумм.

- **CAP-3**
  - **intent:** Analytics может отдельно оценить полноту технических данных.
  - **success:** Underlying `OFFLINE` уменьшает `dataCoverage` даже под manual business override, но не превращается в производственный простой.

- **CAP-4**
  - **intent:** Analytics может выделить события отказа и восстановления из state transitions.
  - **success:** Вход в `DOWN` создаёт failure, выход из `DOWN` в non-`DOWN`/non-`OFFLINE` создаёт recovery, а `OFFLINE` сам не создаёт failure.

- **CAP-5**
  - **intent:** StateRule может отражать реальные переходы без искусственной жёсткой transition matrix.
  - **success:** Любой user state может перейти в другой по rules, тогда как назначение и снятие `OFFLINE` остаётся только за system freshness policy.

## Constraints

- Нормативные определения состояний и переходов находятся в `state-catalog.md`.
- Аддитивные duration facts и базовые отношения метрик находятся в `duration-classification.md`.
- `PLANNED_STOP` исключается из planned production denominator.
- `SETUP` входит в planned production time и снижает Availability.
- `IDLE` входит в operating time и снижает Performance, а не Availability.
- `OFFLINE` является data gap, не downtime и не автоматической loss reason.
- Проценты и коэффициенты вычисляются из сумм и не усредняются между buckets.

## Non-goals

- Полные формулы OEE, Performance, MTBF и MTTR.
- Каталог LossReason и ручная атрибуция причины.
- Жёсткий список допустимых переходов между user states.
- Автоматический incident на каждый transition.
- Производственный календарь, определяющий planned time вне effective states.

## Success signal

Один и тот же набор effective/calculated intervals даёт одинаковые state durations, Availability inputs, failure/recovery events и data coverage во всех аналитических разрезах без трактовки `OFFLINE` как простоя.
