# Модель минутных агрегатов

## Общая граница

Обе проекции используют `bucketStart` в UTC и логический интервал `[bucketStart, bucketStart + 1 minute)`. `bucketStart` выровнен по минуте. Уникальные ключи не допускают две опубликованные версии одного bucket.

## `signal_numeric_rollup_1m`

Проекция создаётся только для числовых `TelemetrySignal` с `signalKind=GAUGE` или `COUNTER`.

| Поле | Назначение |
| --- | --- |
| `signalId`, `bucketStart` | Уникальный ключ |
| `sampleCount` | Все принятые raw-измерения минуты |
| `usableCount` | Измерения, допустимые для числового расчёта |
| `goodCount`, `uncertainCount`, `badCount` | Распределение raw quality |
| `outOfRangeCount` | Число измерений с disqualifying validation flag `OUT_OF_RANGE` |
| `minValue`, `maxValue`, `sumValue` | Агрегаты usable-значений GAUGE |
| `firstValue`, `firstObservedAt` | Первое usable-значение и его event time |
| `lastValue`, `lastObservedAt` | Последнее usable-значение и его event time |
| `deltaValue`, `resetCount` | Производные COUNTER; для GAUGE равны `null` |
| `calculatedAt` | Время публикации текущего результата |

`average = sumValue / usableCount` вычисляется при чтении. При `usableCount=0` числовые aggregates равны `null`. Если принятые samples есть, строка с quality counts сохраняется даже без usable-значений; при полном отсутствии samples строка отсутствует.

## `machine_metric_bucket_1m`

| Поле | Назначение |
| --- | --- |
| `machineId`, `bucketStart` | Уникальный ключ |
| `shiftId`, `shiftDate` | Экземпляр смены; оба `null` для промежутка вне смен |
| `coveredDurationMs` | Часть закрытой минуты внутри coverage машины |
| `runDurationMs`, `idleDurationMs`, `downDurationMs` | Effective business state durations |
| `setupDurationMs`, `plannedStopDurationMs` | Effective manual/business durations |
| `effectiveOfflineDurationMs` | OFFLINE в effective timeline |
| `underlyingOfflineDurationMs` | Технический data gap до manual overlay |
| `producedQuantity`, `scrapQuantity` | Приращения соответствующих COUNTER-сигналов |
| `stopCount`, `failureCount`, `recoveryCount` | Переходы, определённые каталогом метрик и состояний |
| `calculatedAt` | Время публикации текущего результата |

Effective state durations не пересекаются и суммарно равны `coveredDurationMs`. `underlyingOfflineDurationMs` хранится отдельно и может пересекаться с effective manual state.

Для demo MVP у машины может быть не более одного активного сигнала с семантикой `PRODUCTION_COUNT` и не более одного с `SCRAP_COUNT`, если эти метрики используются. При отсутствии такого сигнала соответствующее quantity равно `null`, а не нулю.

## Scope и смена

`shiftId + shiftDate` вычисляются календарём предприятия для `bucketStart`. Границы смен задаются с минутной точностью, поэтому один минутный bucket не принадлежит двум сменам.

Line и Enterprise не получают собственные таблицы: API выбирает machines текущего scope и суммирует их buckets. Перенос Machine между линиями в MVP запрещён; после назначения линии текущая структура применяется и к истории машины.

## `machine_loss_bucket_1m`

Проекция хранит положительные минутные durations по `machineId`, `bucketStart`, `state` и nullable `lossReasonId`. Поддерживаются loss states `IDLE`, `DOWN`, `SETUP` и отдельно отображаемый `PLANNED_STOP`; отсутствие причины означает `UNCLASSIFIED`.

Проекция также содержит `shiftId`, `shiftDate` и `calculatedAt`. Она полностью заменяется для dirty minute вместе с `machine_metric_bucket_1m`; сумма причин одного state не может превышать duration этого state.
