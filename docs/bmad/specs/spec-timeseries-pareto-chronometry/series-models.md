# Модели временных рядов

## Metric series

Scope задаётся как `MACHINE`, `LINE` или `ENTERPRISE` с соответствующим `scopeId`. Каждая point формируется из минутных machine facts и содержит:

```text
bucketStart, bucketEnd
coveredSec
runSec, idleSec, downSec
setupSec, plannedStopSec
effectiveOfflineSec, underlyingOfflineSec
output, scrap
stopCount, failureCount, recoveryCount
availability, performance, quality, oee, dataCoverage
```

Сначала суммируются additive facts point, затем применяются формулы metric catalog. Готовые ratios минут и machines не усредняются. Для Line/Enterprise сохраняются правила совместимости `productionUnit`; несовместимые производственные показатели равны `null`, time metrics остаются доступны.

Покрытый point без событий имеет нулевые counts/durations. Point без coverage имеет `coveredSec=0` и ratios `null`.

## GAUGE series

Точка числового `GAUGE` содержит:

```text
bucketStart, bucketEnd
min, max, avg, first, last
sampleCount, usableCount
goodCount, uncertainCount, badCount
```

`avg` выводится из суммы и usable count исходных минут. Min/max берутся как минимум/максимум минут, first/last — по event time. При отсутствии samples возвращается point с `sampleCount=0`, numeric fields `null`.

## COUNTER series

Точка числового `COUNTER` содержит:

```text
bucketStart, bucketEnd
first, last
delta, resetCount
sampleCount, usableCount
goodCount, uncertainCount, badCount
```

`delta` является суммой минутных delta, а reset count — суммой reset events. First/last выбираются по event time. Gaps не интерполируются.

`STATE`-сигнал не возвращается этим numeric endpoint. Несовместимый kind/value type является ошибкой запроса, а не пустым рядом.
