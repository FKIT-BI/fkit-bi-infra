# Политика доступности

## Приоритеты

Для raw telemetry действует порядок:

```text
доступность сервиса > полнота raw > немедленная согласованность аналитики
```

Это исключение не распространяется на equipment configuration, state rules, manual incidents и generator definitions.

## Realtime degradation

Realtime TelemetrySink использует bounded buffer. Writer отправляет накопленный пакет при достижении 1000 строк либо через 1–2 секунды. Ожидание БД и retry ограничены настройками; бесконечный retry запрещён.

При переполнении буфера отбрасываются старейшие ещё не записанные realtime-пакеты, поскольку свежие значения важнее для текущего состояния. Неуспешный после короткой retry-политики пакет также может быть отброшен. Producer продолжает работу.

Historical run использует отдельную квоту. При давлении он throttles, приостанавливается или завершается ошибкой с checkpoint; он не вытесняет realtime ingestion и query workload.

## Изоляция ресурсов

Analytics использует один Hikari pool на 14–16 соединений. Ingestion, calculation, recalculation и maintenance имеют отдельные semaphore limits, сумма которых не позволяет background workers занять весь pool; query path сохраняет доступный резерв без сложности нескольких pools. Generator использует 2–3 соединения и не позволяет historical занять последний realtime writer slot. Конкретные permits подтверждаются нагрузочным тестом.

Транзакции ingestion и workers короткие. Workers забирают небольшие задания; при нескольких экземплярах могут использовать `FOR UPDATE SKIP LOCKED`. Ошибка одного dirty window не удерживает очередь целиком.

Future partitions создаются заранее. Retention, index build и иные DDL-операции не выполняются на горячем write path.

Historical validation оценивает ожидаемое число measurements и размер БД. При свободном бюджете менее 20% новый historical run приостанавливается или отклоняется; при критическом disk pressure nonessential writers останавливаются раньше query API. `200 measurements/s` является 30-минутным benchmark, а не 90-дневной sizing-гарантией.

## Read availability

Frontend читает `signal_current_value`, `machine_current_state`, state intervals и rollup. Запрос не инициирует и не ожидает расчёт. При lag API возвращает последнюю committed projection со следующей актуальностью:

```text
dataThrough
calculatedAt
stale
```

Raw доступен только ограниченному диагностическому запросу. Тяжёлый raw query имеет statement timeout и не использует query budget без ограничения периода и результата.

## Наблюдаемая потеря

Generator/TelemetrySink публикует как минимум:

```text
generatedMeasurements
acceptedMeasurements
rejectedMeasurements
droppedMeasurements
failedBatches
lastSuccessfulWriteAt
bufferDepth
```

Analytics отслеживает gaps в `producerSequence`, ingestion rate и lag между `observedAt`, `receivedAt` и `dataThrough`. Gap или dropped count не блокирует поток, но доступен в диагностике и логах.
