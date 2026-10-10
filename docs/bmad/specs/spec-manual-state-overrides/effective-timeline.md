# Effective state timeline

## Слои

`calculatedState` принадлежит StateRule projection. `effectiveState` используется для пользовательской timeline и бизнес-агрегации:

```text
effectiveState(T) =
  ManualIncident.stateOverride, если T входит в manual interval
  calculatedState(T), иначе
```

Manual override имеет приоритет только для business state. Underlying `calculatedState`, включая `OFFLINE`, не удаляется и остаётся источником data-quality analytics.

## Проекция

`machine_effective_state_interval` строится асинхронно на объединении boundaries calculated intervals и ManualIncident:

```text
machineId
effectiveFrom
effectiveTo
effectiveState
calculatedState
stateSource: CALCULATED | MANUAL
stateIncidentId?
lossReasonId?
reasonIncidentId?
calculatedAt
```

Даже если manual state не меняется, projection сохраняет границу изменения underlying calculated state, чтобы отдельно посчитать data coverage. Соседние segments объединяются только при совпадении всех state/source/reason/reference fields.

Пример:

```text
calculated: IDLE  [10:00,11:00)
manual:     SETUP [10:15,10:30)

effective:
IDLE  / IDLE / CALCULATED [10:00,10:15)
SETUP / IDLE / MANUAL     [10:15,10:30)
IDLE  / IDLE / CALCULATED [10:30,11:00)
```

Если calculated state внутри manual period равен `OFFLINE`, effective duration относится к manual business state, но тот же segment увеличивает offline/data-gap duration и снижает coverage quality.

## Актуализация

Create/update/close incident создаёт dirty window по объединению прежнего и нового интервала:

```text
dirtyFrom = floor(min(oldFrom,newFrom), UTC minute)
dirtyTo   = ceil(max(oldTo,newTo), UTC minute)
```

Для ongoing boundary `dirtyTo` ограничивается current published `dataThrough`. Пересчитываются effective timeline, state duration buckets, shift metrics и loss attribution. Raw, `signal_current_value` и `machine_state_interval` не пересчитываются.

Background calculation использует staging и атомарную публикацию, как state projection pipeline. До commit read API возвращает прежнюю полную effective projection с currency/recalculating metadata.

## Read model

Frontend получает как минимум:

```text
effectiveState
calculatedState
stateSource
stateIncidentId?
lossReasonId?
reasonIncidentId?
telemetryFreshness/dataQuality
effectiveFrom
effectiveTo
```

Так business override не маскирует технический data gap и остаётся объяснимым.
