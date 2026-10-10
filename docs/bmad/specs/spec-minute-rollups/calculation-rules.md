# Правила расчёта и публикации

## Закрытые минуты

Worker рассчитывает только минуты, для которых `bucketEnd <= dataThrough`. Текущая незакрытая минута не публикуется в rollup. Operational API получает текущие значения и состояние из current projections; исторический ответ не заявляет готовность данных после `dataThrough`.

Первая или последняя закрытая минута coverage может содержать меньше 60 000 ms, если Machine стала `ACTIVE` внутри минуты. Во всех остальных полностью покрытых минутах:

```text
coveredDurationMs = 60_000
```

## GAUGE

В расчёт min/max/sum/first/last входят только usable measurements согласно политике качества сигнала. Порядок определяется `(observedAt, ingestBatchId, ordinal)`, чтобы одинаковый вход всегда давал одинаковые first/last без отдельного measurement ID.

## COUNTER

Измерения сортируются тем же детерминированным порядком. Первой точкой служит `carry-in` — последнее usable-значение до `bucketStart`.

Для каждой следующей пары `previous → current`:

```text
current >= previous: delta += current - previous
current < previous:  delta += current; resetCount += 1
```

В MVP любое отрицательное изменение считается сбросом счётчика. Если `carry-in` отсутствует, первое значение внутри минуты устанавливает baseline и само не добавляется в `delta`. Если внутри минуты недостаточно данных для изменения, `deltaValue=0`; при отсутствии usable-значений `deltaValue=null`.

`producedQuantity` и `scrapQuantity` machine bucket берутся из `deltaValue` сигналов `PRODUCTION_COUNT` и `SCRAP_COUNT` той же минуты.

## State durations и transitions

Machine bucket строится из точных effective и underlying state intervals. Пересечение каждого интервала с минутой даёт duration в миллисекундах. Transition на границе относится bucket, начинающемуся в момент transition.

- вход в `DOWN` увеличивает `failureCount`;
- выход из `DOWN` в non-`DOWN`/non-`OFFLINE` увеличивает `recoveryCount`;
- переход из `RUN` в `IDLE` или `DOWN` увеличивает `stopCount`;
- `OFFLINE` сам не создаёт failure или recovery.

## Повторный расчёт

Новые, late и historical measurements объединяются в dirty minute ranges. Worker:

1. читает исходные raw facts и точные state intervals для диапазона;
2. рассчитывает полный набор новых numeric, machine и loss rows во временное staging-представление;
3. в короткой транзакции удаляет прежние строки диапазона и вставляет согласованный новый набор;
4. продвигает `dataThrough` только после успешной публикации.

Увеличение существующих значений через `+=` запрещено: retry должен воспроизводить тот же итог. PostgreSQL MVCC позволяет query API продолжать читать предыдущий committed результат до завершения короткой публикации.

## Длительные периоды

API суммирует минутные numerators и counters, затем вычисляет производные показатели. Неполная минута на границе произвольного запроса в demo MVP не достраивается из raw: API выравнивает аналитический период по доступным закрытым минутам и возвращает фактические `from`, `to` и `dataThrough`.

Часовые и дневные таблицы добавляются только если нагрузочный тест покажет неприемлемую задержку чтения минутных данных.
