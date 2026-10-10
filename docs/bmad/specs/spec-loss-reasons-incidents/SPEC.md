---
id: SPEC-loss-reasons-incidents
companions:
  - loss-reason-model.md
  - manual-incident-model.md
  - attribution-and-lifecycle.md
sources: []
---

> **Canonical contract.** Этот SPEC и файлы из `companions:` составляют полный контракт каталога причин и ручной классификации потерь demo MVP.

# Причины потерь и ManualIncident

## Why

Пользователь должен объяснять `IDLE`, `DOWN`, `SETUP` и `PLANNED_STOP`, а при необходимости вручную исправлять бизнес-состояние, не изменяя raw telemetry и calculated timeline. MVP нужна одна детерминированная модель без отдельной incident-платформы и нескольких конкурирующих причин.

## Capabilities

- **CAP-1**
  - **intent:** Enterprise может управлять собственным каталогом причин потерь.
  - **success:** Причины имеют стабильный код, закрытую категорию и ACTIVE/DISABLED lifecycle; отключение не меняет существующую историю.

- **CAP-2**
  - **intent:** Пользователь может одним ManualIncident задать state override, loss reason либо оба эффекта.
  - **success:** Условно обязательные `stateOverride/lossReasonId` образуют один из трёх однозначных effect types без второй доменной сущности.

- **CAP-3**
  - **intent:** Система может детерминированно совместить независимые интервалы состояния и причины.
  - **success:** В один момент действует не более одного override и одной reason, тогда как state-only и reason-only incidents могут пересекаться.

- **CAP-4**
  - **intent:** Пользователь может исправить, закрыть или отменить ручную классификацию.
  - **success:** Mutation проверяет границы и overlaps, сохраняет строку при cancel и асинхронно публикует согласованные effective и loss projections.

- **CAP-5**
  - **intent:** Причинная аналитика остаётся объяснимой после state recalculation и при data gaps.
  - **success:** Reason применяется только к eligible effective states, не изменяет RUN/OFFLINE или underlying quality и воспроизводится из сохранённого incident interval.

## Constraints

- Каталог причин и правила изменяемости находятся в `loss-reason-model.md`.
- Поля и validation ManualIncident находятся в `manual-incident-model.md`.
- Overlap, attribution, lifecycle и dirty recalculation находятся в `attribution-and-lifecycle.md`.
- В один момент у Machine может быть максимум одна причина потери.
- ManualIncident не изменяет raw telemetry и calculated state intervals.
- Открытая reason annotation классифицирует новые eligible intervals до закрытия.
- Enum используется для закрытого `LossCategory`; пользовательские LossReason остаются строками таблицы.

## Non-goals

- Несколько одновременных причин, primary/secondary cause и causal hierarchy.
- Версии LossReason и полный журнал версий incident.
- Пользовательский CRUD категорий причин.
- Future scheduling ManualIncident.
- Автоматическое определение причины по telemetry.
- Авторизация пользователя не доказывает достоверность переданного `author`; identity mapping и полный audit остаются вне MVP.

## Success signal

Оператор выбирает интервал потери в Chronometry, назначает причину либо ручной SETUP/PLANNED_STOP, после фоновой публикации те же границы и причина появляются в timeline, loss buckets и Pareto; overlapping causes отклоняются, а отключённая причина сохраняется в истории.
