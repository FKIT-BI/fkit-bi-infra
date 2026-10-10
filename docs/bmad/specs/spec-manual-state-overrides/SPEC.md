---
id: SPEC-manual-state-overrides
companions:
  - manual-interval-model.md
  - effective-timeline.md
sources: []
---

> **Canonical contract.** Этот SPEC и файлы из `companions:` составляют focused-контракт ручных `SETUP/PLANNED_STOP` overlays; полный ManualIncident и LossReason определены в соседнем `spec-loss-reasons-incidents`.

# Ручная классификация состояния

## Why

Не каждая переналадка или плановая остановка однозначно определяется телеметрией. Оператору нужна возможность задать фактические границы и бизнес-классификацию, не изменяя raw или рассчитанную StateRule timeline, чтобы последующий replay не потерял человеческое подтверждение.

## Capabilities

- **CAP-1**
  - **intent:** Пользователь может вручную указать период `SETUP` или `PLANNED_STOP` машины.
  - **success:** Валидный past/current полуоткрытый интервал сохраняется как ManualIncident отдельно от calculated state и не пересекает другой override этой машины.

- **CAP-2**
  - **intent:** Пользователь может исправить границы и классификацию либо закрыть продолжающийся ручной период.
  - **success:** Изменение выполняется атомарно, сохраняет identity/owner и создаёт dirty range по объединению старых и новых границ.

- **CAP-3**
  - **intent:** Система может построить единую пользовательскую timeline из автоматического состояния и ручной классификации.
  - **success:** Внутри incident `effectiveState` равен manual override, вне его — `calculatedState`; исходное техническое состояние остаётся доступным.

- **CAP-4**
  - **intent:** Система может актуализировать зависимую аналитику без replay raw и StateRule.
  - **success:** После изменения incident асинхронно пересчитываются effective intervals, длительности, shift metrics и losses, а raw и `machine_state_interval` не меняются.

- **CAP-5**
  - **intent:** Frontend может одновременно объяснить бизнес-классификацию и качество технических данных.
  - **success:** Effective response содержит effective/calculated state, source, incident reference и telemetry quality; manual period поверх `OFFLINE` не скрывает data gap.

## Constraints

- Поля, границы, overlap validation и command API определены в `manual-interval-model.md`.
- Алгоритм наложения, dirty ranges и read model определены в `effective-timeline.md`.
- Поле `stateOverride` допускает только `SETUP` и `PLANNED_STOP`; единый ManualIncident может вместо него содержать только `lossReasonId`.
- ManualIncident не изменяет raw telemetry и calculated `machine_state_interval` и переживает их повторный replay.
- Future scheduling ручных периодов не входит в MVP.
- Effective projection и aggregates обновляются асинхронно; frontend до публикации читает предыдущий полный результат.

## Non-goals

- Ручное назначение `RUN`, `IDLE`, `DOWN` или `OFFLINE`.
- Редактирование calculated state intervals.
- Future planned-stop schedule.
- Несколько одновременных state overrides или reasons.
- Полный audit/version history ManualIncident.
- Автоматическое создание manual incident из telemetry.

## Success signal

Пользователь отмечает точный период переналадки или плановой остановки, при необходимости назначает причину, frontend и агрегаты получают effective state/reason, а повторный расчёт telemetry сохраняет ручную классификацию и одновременно показывает исходный calculated/offline state.
