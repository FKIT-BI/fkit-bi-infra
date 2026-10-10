# Агрегация и сравнение

## Machine → Line → Enterprise

Machine bucket содержит additive facts. Для Line и Enterprise API сначала суммирует их по всем участвующим machines:

```text
state durations
coveredTime
underlyingOfflineTime
output
scrap
idealOutput
stopCount
failureCount
recoveryCount
```

После суммирования заново вычисляются Availability, Performance, Quality, OEE, data coverage, MTBF и MTTR. Усреднение процентов отдельных machines или buckets запрещено.

Durations уровня Line/Enterprise являются machine-time: десять машин, покрытых одну минуту, дают 600 секунд `coveredTime`, а не 60 секунд календарного интервала.

## Совместимость выпуска

`output`, `scrap`, `idealOutput`, Performance, Quality и OEE агрегируются только тогда, когда все участвующие в расчёте machines с производственными данными используют одну `productionUnit` и имеют необходимые inputs.

Если units различаются или обязательные inputs отсутствуют, производственные aggregate metrics равны `null`. Time metrics, Availability, data coverage и event counts продолжают рассчитываться.

Machine без output/nominal configuration не подмешивается в производственный denominator как ноль. Наличие таких machines отражается diagnostic metadata будущего API.

## Previous period

Для обычного диапазона `[from,to)`:

```text
duration = to - from
current  = [from, to)
previous = [from - duration, from)
```

Для запроса конкретного экземпляра `shiftId + shiftDate` previous является предыдущим календарным occurrence той же Shift, разрешённым тем же календарём предприятия.

Current и previous независимо ограничиваются доступными закрытыми минутами. Каждый результат имеет собственные фактические `from`, `to` и `dataThrough`; сравнение не заставляет worker синхронно достраивать отсутствующую аналитику.
