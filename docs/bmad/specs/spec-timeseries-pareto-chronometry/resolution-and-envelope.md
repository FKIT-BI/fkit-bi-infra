# Resolution и общий envelope

## Период

Все запросы используют полуоткрытый интервал `[from,to)`, где `from<to`. Максимальная длительность одного запроса demo MVP — 90 дней. Данные после `dataThrough` не заявляются готовыми.

Shift-фильтр задаётся `shiftId`. Один экземпляр смены задаётся `shiftId + shiftDate`; системных `day/night` нет. Timezone берётся из Enterprise.

## Resolution

Допустимые значения запроса:

```text
AUTO | 5m | 15m | 1h | 1d
```

AUTO выбирается по исходной длительности запроса:

| Период | Resolution |
| --- | --- |
| До 12 часов включительно | `5m` |
| Более 12 часов, до 2 дней включительно | `15m` |
| Более 2 дней, до 14 дней включительно | `1h` |
| Более 14 дней, до 90 дней включительно | `1d` |

`5m`, `15m` и `1h` выравниваются по UTC. `1d` соответствует локальному календарному дню Enterprise; при DST он может длиться 23 или 25 часов. Каждый point всегда содержит фактические `bucketStart` и `bucketEnd` как UTC instants.

Для telemetry series сервер дополнительно укрупняет запрошенную resolution до целого числа минут, если иначе получится более 720 points. Применённая resolution возвращается в ответе.

Metric и loss series ограничены 1000 points. В режиме `AUTO` backend укрупняет resolution до соблюдения лимита. Если явно запрошенная resolution превышает лимит, запрос отклоняется с `RESULT_TOO_LARGE`, а не возвращает усечённый ряд.

## Envelope

Общие metadata исторического ответа:

```text
requestedFrom
requestedTo
actualFrom
actualTo
dataThrough
calculatedAt
partial
resolution
points
```

`actualFrom/actualTo` описывают реально возвращённый закрытый диапазон. `partial=true`, если запрос обрезан по coverage, `dataThrough` или доступным закрытым минутам. Lag не блокирует запрос.

Период целиком вне coverage возвращает пустой `points`. Metric и loss series возвращают каждый bucket внутри `actualFrom/actualTo`: отсутствие события или потери выражается нулём, а `coveredSec=0` сопровождается `null` ratios. Telemetry series также возвращает каждый bucket этого диапазона, но отсутствие samples выражает `sampleCount=0` и `null` numeric values.
