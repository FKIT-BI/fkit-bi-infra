# Каталог показателей

Все durations внутри расчётов выражаются в миллисекундах. API может отдавать секунды или минуты только как транспортное представление одного и того же значения.

## Время

```text
coveredTime =
    runTime
  + idleTime
  + downTime
  + setupTime
  + plannedStopTime
  + effectiveOfflineTime

plannedProductionTime =
    runTime
  + idleTime
  + downTime
  + setupTime

operatingTime = runTime + idleTime
productiveTime = runTime
```

`PLANNED_STOP` исключён из planned production. `OFFLINE` является data gap. `SETUP` входит в planned production и снижает Availability. `IDLE` означает доступную, но не производящую машину.

## Availability и data coverage

```text
availability = operatingTime / plannedProductionTime

dataCoverage =
  (coveredTime - underlyingOfflineTime) / coveredTime
```

`availability=null`, если `plannedProductionTime<=0`. `dataCoverage=null`, если `coveredTime<=0`. Underlying OFFLINE сохраняет технический gap даже под manual override.

## Выпуск

`PRODUCTION_COUNT` означает все завершённые изделия, включая брак. `SCRAP_COUNT` означает бракованные изделия в той же `productionUnit`.

```text
output = sum(production counter delta)
scrap = sum(scrap counter delta)
goodOutput = output - scrap
```

Без соответствующего сигнала `output` или `scrap` равен `null`. Отсутствие измерений не означает нулевой выпуск.

## Performance, Quality и OEE

Machine `nominalRate` задаётся в `productionUnit` за час.

```text
idealOutput = nominalRatePerHour × operatingTimeMs / 3_600_000
performance = output / idealOutput
quality = (output - scrap) / output
oee = availability × performance × quality
```

Null semantics:

| Показатель | Равен `null`, когда |
| --- | --- |
| `idealOutput` | Нет `nominalRate`, `productionUnit` или `operatingTime<=0` |
| `performance` | Нет `output` либо `idealOutput<=0` |
| `quality` | Нет `output`, нет `scrap`, `output<=0` либо `scrap>output` |
| `oee` | Любой из Availability, Performance или Quality равен `null` |

`scrap>output` дополнительно создаёт diagnostic warning. Performance не обрезается на 100%: превышение остаётся видимым как возможная аномалия или неверный норматив.

## Остановки и надёжность

```text
stopCount = count(RUN → IDLE or RUN → DOWN)

failureCount =
  count(non-DOWN/non-OFFLINE → DOWN)

recoveryCount =
  count(DOWN → non-DOWN/non-OFFLINE)

mtbf = operatingTime / failureCount
mttr = downTime / failureCount
```

При `failureCount=0` MTBF и MTTR равны `null`. Для demo MVP MTTR отражает среднее DOWN-время на зарегистрированный failure, включая незавершённый текущий DOWN; отдельное pairing failure/repair не выполняется.

## Отличия от draft API

- `coveredSec` заменяет неоднозначный `calendarSec`.
- `idleSec` возвращается отдельно; IDLE не включается в unplanned downtime.
- `downSec`, `setupSec` и `plannedStopSec` возвращаются отдельно.
- Availability использует `operatingTime / plannedProductionTime`.
- Performance использует nominal output за `RUN + IDLE`, а не только RUN.
- Добавляются `scrap`, `quality`, `oee`, `dataCoverage`, `failureCount` и `recoveryCount`.
