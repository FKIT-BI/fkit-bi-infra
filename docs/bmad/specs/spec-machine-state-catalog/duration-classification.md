# Классификация длительностей

## Effective state facts

Для выбранного периода effective intervals образуют непересекающееся разложение:

```text
coveredDuration =
    runDuration
  + idleDuration
  + downDuration
  + setupDuration
  + plannedStopDuration
  + effectiveOfflineDuration
```

Manual override может заменить effective `OFFLINE`, поэтому технический gap дополнительно считается по underlying calculated timeline как `underlyingOfflineDuration` и может пересекаться с manual business duration.

## Базовые суммы

```text
plannedProductionTime =
    runDuration
  + idleDuration
  + downDuration
  + setupDuration

operatingTime =
    runDuration
  + idleDuration

productiveTime =
    runDuration
```

При положительном denominator:

```text
availability = operatingTime / plannedProductionTime
```

При нулевом `plannedProductionTime` Availability равна `null`, а не `0` или `100%`.

`IDLE` не снижает Availability, потому что Machine считается доступной, но снижает последующий Performance через отсутствие ожидаемого выпуска. Точная формула Performance определяется metric spec.

## Data coverage

При положительном coverage:

```text
dataCoverage =
  (coveredDuration - underlyingOfflineDuration)
  / coveredDuration
```

При нулевом coverage значение `null`. Manual state может дать известную бизнес-классификацию поверх gap, но underlying offline duration всё равно снижает data coverage.

## Aggregation law

Buckets хранят duration numerators, output counts и event counts. API сначала суммирует facts за период и только затем вычисляет ratios. Готовые Availability, Performance или dataCoverage разных machines, shifts и buckets не усредняются.
