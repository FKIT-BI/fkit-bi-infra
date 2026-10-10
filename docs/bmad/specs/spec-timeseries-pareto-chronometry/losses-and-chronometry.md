# Losses, Pareto и Chronometry

## Минутная причинная проекция

`machine_loss_bucket_1m` содержит только положительные пересечения effective loss intervals с закрытой минутой:

| Поле | Назначение |
| --- | --- |
| `machineId`, `bucketStart` | Машина и UTC-минута |
| `shiftId`, `shiftDate` | Экземпляр смены либо `null` вне смены |
| `state` | `IDLE`, `DOWN`, `SETUP` или отдельно отображаемый `PLANNED_STOP` |
| `lossReasonId` | Причина или `null` для `UNCLASSIFIED` |
| `durationMs` | Длительность сочетания state/reason внутри минуты |
| `calculatedAt` | Время публикации |

Логический ключ — `machineId + bucketStart + state + nullable lossReasonId`. Сумма строк одного state не может превышать его duration в `machine_metric_bucket_1m`. Проекция полностью заменяется для dirty minutes и публикуется согласованно с machine metrics.

До назначения причин IDLE/DOWN/SETUP остаются функционально видимыми как `UNCLASSIFIED`. Точный доменный поток назначения причины определяется Incident/LossReason spec.

## Loss timeseries

Loss denominator MVP:

```text
totalLoss = idleDuration + downDuration + setupDuration
```

`PLANNED_STOP` возвращается отдельно, но не входит в `totalLoss`. `OFFLINE` является data gap и не относится к loss reason.

Каждая point содержит:

```text
bucketStart, bucketEnd
idleSec, downSec, setupSec, plannedStopSec
unclassifiedLossSec
byReason[] { reasonId: UUID|null, durationSec }
```

Массив используется вместо JSON-map, потому что `reasonId=null` имеет нормативный смысл.

Чтобы число series не росло вместе со справочником, запрос принимает `top` named reasons: по умолчанию 5, максимум 20. `UNCLASSIFIED` при наличии всегда возвращается отдельно, остальные причины за пределами top объединяются в `OTHER` в каждом временном bucket.

## Pareto

Строка Pareto содержит reason/category, duration, share и cumulative share. Правила:

- сортировка по duration descending, затем по стабильному коду причины;
- `reasonId=null` при наличии всегда отображается как отдельный `UNCLASSIFIED`;
- `top` по умолчанию 5, максимум 20 и применяется к named reasons;
- named reasons после top объединяются в `OTHER`;
- `share=duration/totalLoss`;
- `cumulativeShare` — накопительная сумма отсортированных shares;
- при наличии `OTHER` shares всех возвращённых строк дают 1;
- при `totalLoss=0` возвращается пустой список.

## Chronometry

MVP-запрос задаёт `machineId + shiftDate` и необязательный `shiftId`. С указанным `shiftId` ответ содержит одну occurrence; без него — все Shift occurrences, начинающиеся в эту локальную дату, по `sortOrder`, затем `code`. Каждая occurrence содержит boundaries, readiness metadata, totals по state и точные effective intervals:

```text
state
from, to, durationSec
calculatedState
source: CALCULATED | MANUAL
incidentId
lossReasonId
telemetryQuality
```

Intervals обрезаются границами occurrence и `dataThrough`, сортируются по `from`, не пересекаются и покрывают готовую часть смены. Текущий открытый interval получает фактический `to=dataThrough` в ответе, не изменяя сохранённую open boundary.

Один полный ответ по всем occurrences ограничен 10 000 intervals. При превышении backend возвращает `CHRONOMETRY_TOO_LARGE` и не отдаёт усечённую timeline.

Группировка тех же intervals по причинам в Chronometry не возвращается: это дублировало бы данные. Top причин предоставляет Pareto.
