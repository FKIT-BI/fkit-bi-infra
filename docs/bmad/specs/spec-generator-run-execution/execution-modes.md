# Режимы выполнения

## REALTIME

Immediate Run создаётся `QUEUED`, при получении execution slot переходит в `RUNNING` и фиксирует `startedAt`. `eventFrom` равен фактическому началу wall-clock generation. API может передать `durationMs` или `eventTo`; без них `LOOP` выполняется до stop, а `ONCE` — до конца первой phase sequence.

Каждый signal имеет собственный tick schedule. Если процесс, GC или PostgreSQL задержали обработку, ticks с due time в прошлом пропускаются. Generator не формирует catch-up burst; число пропущенных measurements учитывается в диагностике. Следующий measurement получает актуальный scheduled wall-clock `observedAt` и проходит обычный future-skew contract.

## HISTORICAL

Request задаёт полуоткрытый UTC-диапазон `[from,to)`:

- `from < to`;
- `to <= acceptedAt` Run;
- `from` не раньше границы активного 90-дневного raw window, вычисленной по времени PostgreSQL;
- длительность не более 90 days;
- отдельный timezone параметр отсутствует;
- диапазон не пересекает ранее подтверждённое generator coverage той же Machine.

До перехода в `QUEUED` readiness подтверждает, что все UTC-day raw partitions диапазона уже attached и имеют обязательный индекс. Generator не создаёт partitions и не получает DDL-права.

Virtual clock начинается в `from`. `LOOP` повторяет phase sequence до `to`; `ONCE` завершает Run после одного sequence, даже если остаётся незаполненная часть requested range. `generatedThrough` отражает фактически достигнутую границу.

Writer работает с throttling 1000–2000 measurements/s и одним historical execution на минимальном host. Historical Run может сосуществовать с realtime, но его quota уменьшается при росте API latency, connection pressure, realtime lag или calculation backlog.

## SCHEDULED

Scheduled Run принимает будущий `scheduledStartAt` с обязательным offset и сохраняет UTC instant. Enterprise timezone используется frontend только для ввода и отображения. До срока measurements не создаются.

В момент старта generator повторно проверяет current ownership, line assignment и `ACTIVE` обязательных сущностей, не перестраивая snapshot. При успехе Run переходит `QUEUED` и далее выполняется по realtime semantics.

Misfire policy:

- задержка `<=30 seconds`: запуск начинается немедленно, пропущенные ticks не восстанавливаются;
- задержка `>30 seconds`: `FAILED`, `failureCode=SCHEDULE_MISSED`, `retryable=false`;
- stop до начала: `CANCELLED`.

Bounded scheduled Run использует `durationMs` или `eventTo`. Unbounded `LOOP` допускается и требует ручного stop; `ONCE` без внешней границы заканчивается после одной phase sequence.
