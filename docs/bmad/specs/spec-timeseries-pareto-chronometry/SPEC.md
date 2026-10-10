---
id: SPEC-timeseries-pareto-chronometry
companions:
  - resolution-and-envelope.md
  - series-models.md
  - losses-and-chronometry.md
sources: []
---

> **Canonical contract.** Этот SPEC и файлы из `companions:` составляют полный контракт исторических рядов, Pareto и хронометража demo MVP.

# Timeseries, Pareto и Chronometry

## Why

Demo MVP должен показывать не только итоговые карточки, но и объяснимую динамику телеметрии, состояний и потерь. При этом чтение не должно сканировать raw telemetry или собирать причины из точных intervals для каждого пользовательского запроса.

## Capabilities

- **CAP-1**
  - **intent:** Пользователь может просмотреть динамику производственных показателей для Machine, Line или Enterprise.
  - **success:** Каждая точка содержит суммарные факты и заново рассчитанные ratios, а весь ряд сообщает фактические границы и готовность данных.

- **CAP-2**
  - **intent:** Пользователь может просмотреть числовой telemetry signal за выбранный период.
  - **success:** GAUGE и COUNTER возвращают не более 720 точек с агрегацией, качеством и явными gaps без тяжёлого raw query.

- **CAP-3**
  - **intent:** Пользователь может анализировать динамику и Pareto производственных потерь.
  - **success:** IDLE, DOWN и SETUP распределяются по причинам или `UNCLASSIFIED`, top дополняется `OTHER`, а shares возвращённых строк суммарно равны единице.

- **CAP-4**
  - **intent:** Пользователь может просмотреть точный хронометраж одной машины за одну либо все смены выбранной локальной даты.
  - **success:** Ответ с optional `shiftId` возвращает соответствующие occurrences, а их effective intervals не пересекаются, обрезаны по смене и готовности расчёта и сохраняют calculated/manual source, incident, reason и telemetry quality.

- **CAP-5**
  - **intent:** Frontend может одинаково различать нулевые, отсутствующие, неполные и устаревшие исторические данные.
  - **success:** Каждый ответ содержит requested/actual boundaries, `dataThrough`, `partial` и применённую resolution; пустой coverage не выглядит как нулевая работа.

## Constraints

- Границы запросов, resolution и metadata определены в `resolution-and-envelope.md`.
- Формы metric и telemetry series определены в `series-models.md`.
- Loss timeseries, Pareto и Chronometry определены в `losses-and-chronometry.md`.
- Исторический запрос не ждёт recalculation и читает последнюю committed projection.
- Физически сохраняется только минутный уровень; response buckets крупнее минуты собираются при чтении.
- Telemetry series не интерполирует отсутствующие значения.
- Metric/loss series ограничены 1000 points, telemetry series — 720 points, полный Chronometry response — 10 000 целых intervals.
- Причинная аналитика читает `machine_loss_bucket_1m`, а не выполняет тяжёлое соединение точных intervals на каждый запрос.

## Non-goals

- Физические таблицы `5m`, `15m`, `1h` и `1d`.
- Произвольный пользовательский размер bucket.
- Исторический series для категориальных `STATE`-сигналов.
- Waveform, raw oscillogram и более 720 telemetry points в одном ответе.
- Редактор LossReason и назначение причины — они определяются отдельным доменным блоком.
- Межмашинный Chronometry и realtime streaming графиков.

## Success signal

За период до 90 дней frontend получает ограниченные и объяснимые metric/telemetry/loss series, Pareto и сменный Chronometry из подготовленных минутных данных; ответы не блокируют ingestion, показывают gaps и lag, а изменение причины актуализируется через тот же dirty-window pipeline.
