# Правила качества и актуальности

## Пригодность значения

Raw measurement является usable, если одновременно:

```text
sourceQuality = GOOD
нет validation flag OUT_OF_RANGE
```

`sourceQuality` независимо хранит `GOOD`, `UNCERTAIN` или `BAD`. В MVP `OUT_OF_RANGE` является disqualifying validation flag. `CLOCK_SKEW` остаётся диагностическим признаком: допустимое событие используется не раньше собственного `observedAt`. Флаги `SOURCE_UNCERTAIN` и `SOURCE_BAD` не используются, поскольку дублировали бы `sourceQuality`.

`UNCERTAIN`, `BAD` и out-of-range measurement:

- сохраняются в raw;
- могут быть показаны как последнее полученное значение;
- не заменяют последнее usable значение;
- не входят в числовые min/max/sum/avg и counter delta;
- увеличивают отдельные quality counters rollup.

Missing measurement означает отсутствие строки. `null`, `NaN` и infinity не являются состоянием качества и отклоняются ingestion.

## Freshness

Freshness вычисляется относительно `referenceTime`:

| Условие | Результат |
| --- | --- |
| Последнего usable значения нет | `NO_DATA` |
| `referenceTime - lastUsableObservedAt <= staleAfterMs` | `FRESH` |
| Разница больше `staleAfterMs` | `STALE` |

Для current API `referenceTime` равен текущему времени backend. Для исторического evaluator это event time восстанавливаемой точки.

Если `staleAfterMs = null`, сигнал можно показывать и агрегировать, но нельзя использовать в `StateRule`. Полная валидация rule set отклоняет ссылку на такой сигнал.

Когда вход правила становится `NO_DATA` или `STALE`, его значение в выражении равно `UNKNOWN`. Трёхзначная логика и результат набора правил определяются соседней спецификацией StateRule.

## OFFLINE машины

`offlineAfterMs` принадлежит конфигурации расчёта состояния машины, а не отдельному сигналу. Значение положительное; default MVP — `60_000`.

Для точки `T` машина находится в `OFFLINE`, если в полуоткрытом интервале

```text
(T - offlineAfterMs, T]
```

нет ни одного принятого raw measurement этой машины. Учитывается любое принятое качество, поскольку `OFFLINE` отвечает за наличие канала связи, а не достоверность физического значения. Historical measurement с event time в прошлом не освежает current connectivity.

Если telemetry для машины ещё никогда не поступала, current state равен `OFFLINE`. Проверка выполняется до пользовательских правил; rule не может переопределить этот результат.

## Rollup качества

Для каждого бакета сохраняются как минимум:

```text
samplesCount
goodSamplesCount
uncertainSamplesCount
badSamplesCount
outOfRangeSamplesCount
```

Значения `GAUGE` и `COUNTER` рассчитываются только по usable samples. Quality counts позволяют frontend отличить реальную величину от неполного или недостоверного покрытия.
