# Модель GenerationRun

## Поля

| Поле | Правило |
|---|---|
| `id` | UUID запуска |
| `scenarioId` | Scenario, из которого создан snapshot |
| `enterpriseId` | Дублируется для ownership/filtering |
| `mode` | `REALTIME|HISTORICAL|SCHEDULED` |
| `status` | Операционный lifecycle |
| `snapshot` | Immutable Scenario + необходимые Machine/Component/Signal данные |
| `randomSeed` | Явный или сгенерированный backend `long` |
| `eventFrom`, `eventTo` | Event-time coverage; `eventTo` может отсутствовать у realtime |
| `scheduledStartAt` | Обязателен только для `SCHEDULED` |
| `requestedAt`, `startedAt`, `finishedAt` | Фактические timestamps |
| `stopRequestedAt` | Время принятия stop command |
| `checkpoint` | Последняя подтверждённая позиция генерации |
| counters | generated, written, dropped measurements и failed batches |
| `failureCode`, `failureMessage` | Ограниченная terminal diagnostics |

Snapshot содержит только необходимые generator поля и typed signal definitions. Он не ссылается на номер machine configuration или Scenario version.

## Lifecycle

```text
SCHEDULED -> QUEUED -> RUNNING -> COMPLETED
                |          |  \
                |          |   -> FAILED
                |          -> STOP_REQUESTED -> STOPPED
                -> CANCELLED
SCHEDULED -> CANCELLED
```

- Immediate realtime/historical Run создаётся `QUEUED`.
- Future Run создаётся `SCHEDULED`, а в срок переходит `QUEUED` после readiness revalidation.
- `COMPLETED`, `STOPPED`, `CANCELLED`, `FAILED` terminal.
- Повторный stop terminal Run идемпотентно возвращает текущее состояние.
- Stop не обрывает batch transaction: текущий batch завершается либо откатывается, новые пакеты не формируются.

Точная семантика event time, progress, checkpoint и retry определяется sibling-контрактом `../spec-generator-run-execution/`.

## Snapshot и revalidation

Snapshot создаётся атомарно с Run. Immediate Run использует его без повторного чтения current equipment. Scheduled Run перед фактическим стартом повторно проверяет current ownership, line assignment и `ACTIVE` необходимых Enterprise/Line/Machine/Signal. Ошибка переводит Run в `FAILED` до первой telemetry write; сохранённый snapshot остаётся для диагностики.

Изменение или disable после перехода в `RUNNING` не останавливает Run: он заканчивает работу по snapshot.

## Конкурентность

- Одна Machine участвует не более чем в одном `RUNNING|STOP_REQUESTED` realtime execution.
- Future reservations одной Machine не пересекаются по плановому интервалу.
- Multi-machine Run резервирует весь набор атомарно; частичный старт запрещён.
- На минимальном host выполняется один historical Run. Он может сосуществовать с realtime, использует отдельную квоту и throttling.
- Конфликт возвращает business error со всеми занятыми machine IDs; frontend не должен повторять запрос автоматически без изменения условий.

## Интеграционная граница

Frontend выбирает Enterprise/Line/Machine/Signal через Analytics API и передаёт UUID в Generator API. Generator самостоятельно проверяет ссылки по общей PostgreSQL и не требует синхронного HTTP-вызова Analytics.

При публикации raw Run использует `TelemetrySink.writeBatch`; measurement содержит `signalId`, `observedAt`, типизированное value, source quality и flags. `generatorRunId` сохраняется в batch header. Состояние машины, `shiftId`, KPI и intervals не входят в payload.
