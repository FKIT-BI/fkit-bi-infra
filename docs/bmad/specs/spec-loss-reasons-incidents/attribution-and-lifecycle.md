# Наложение и жизненный цикл

## Независимые измерения

Overlap проверяется отдельно:

- два non-cancelled incidents со `stateOverride` не пересекаются;
- два non-cancelled incidents с `lossReasonId` не пересекаются;
- state-only и reason-only incidents могут пересекаться.

Incident с обоими эффектами участвует в обеих проверках. Конфликт возвращает `409` с отдельным code для state или reason overlap.

## Attribution

1. Calculated intervals разрезаются по границам state incidents.
2. Manual SETUP/PLANNED_STOP формирует effective state.
3. Effective intervals разрезаются по границам reason incidents.
4. Reason применяется к `IDLE`, `DOWN`, `SETUP`, `PLANNED_STOP` и игнорируется на RUN/OFFLINE.
5. Результат публикуется в effective intervals, machine metrics и loss buckets.

Effective projection хранит:

```text
machineId
effectiveFrom, effectiveTo
effectiveState, calculatedState
stateSource: CALCULATED | MANUAL
stateIncidentId?
lossReasonId?
reasonIncidentId?
calculatedAt
```

State incident с собственной reason может иметь одинаковые `stateIncidentId/reasonIncidentId`. При наложении разных state-only и reason-only incidents ссылки различаются. Manual state поверх underlying OFFLINE не скрывает `underlyingOfflineDuration`.

## Mutations и dirty range

Create/update/close/cancel создаёт minute-aligned union прежнего и нового интервала. Для ongoing end ограничивается текущим `dataThrough`.

Асинхронно пересчитываются и вместе публикуются:

```text
machine_effective_state_interval
machine_metric_bucket_1m
machine_loss_bucket_1m
```

Raw telemetry, signal rollup и calculated `machine_state_interval` не меняются. До commit API читает прежний полный результат с `recalculating=true`.

Cancel устанавливает `cancelledAt` и прекращает оба эффекта. Строка остаётся доступна с `includeCancelled=true`; восстановление и физическое удаление в MVP отсутствуют.
