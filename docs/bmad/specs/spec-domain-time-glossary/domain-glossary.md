# Словарь домена и временных полей

## Производственные сущности

| Термин | Канонический смысл |
|---|---|
| Enterprise | Организация данных производственной площадки; владеет линиями, машинами, сменами и справочником причин потерь. Не задаёт пользовательскую ACL. |
| ProductionLine | Именованная линия Enterprise; Machine может оставаться неназначенной до пакетного назначения. |
| Machine | Оборудование и основной scope состояния, генерации raw telemetry и аналитики. |
| Component | Узел конечного дерева внутри Machine; Sensor/Instrument — значения `Component.kind`, отдельные сущности не вводятся. |
| TelemetrySignal | Настроенный источник одного типизированного значения; может быть связан с Machine или её Component. |
| Measurement | Неизменяемый raw факт одного `signalId`, одного типизированного value и `observedAt`; состояние машины в нём не передаётся. |
| MachineState | Каталогизированное состояние, выводимое Analytics из сигналов и правил; Generator не назначает его напрямую. |
| State interval | Полуоткрытый рассчитанный период одного состояния; ручные overrides образуют отдельный effective layer. |
| ManualIncident | Ручная запись причины/границ потери Machine, инициирующая async актуализацию аналитических read models. |
| LossReason | Настраиваемая Enterprise-owned причина потери; `UNCLASSIFIED` — отсутствие причины, `OTHER` — только bucket аналитического ответа. |
| ShiftOccurrence | Одно фактическое вхождение календарного Shift; ключ — `shiftId + shiftDate`, где date — локальная дата старта. |
| Bucket | Ограниченный аналитический интервал, начало UTC-aligned для минутных проекций; содержит аддитивные агрегаты периода. |

## Временные поля

| Поле | Значение |
|---|---|
| `observedAt` | Event time измерения, заданный источником/Generator. Порядок вставки его не заменяет. |
| `receivedAt` | Время записи заголовка ingest batch, назначаемое PostgreSQL; общее для его measurements. |
| `calculatedAt` | Wall-clock время расчёта/публикации конкретной projection, не граница полноты данных. |
| `dataThrough` | Исключительная UTC-minute boundary полного опубликованного исторического coverage; позднее событие может инициировать исправление уже опубликованного участка. |
| `effectiveFrom`, `effectiveTo` | Бизнес/event-time boundaries effective state interval; интервал включает начало и исключает конец. `effectiveTo = null` означает продолжающийся интервал. |
| `detectedAt` | Processing/wall-clock время, когда evaluator обнаружил или материализовал event-time переход; отличается от `effectiveFrom`, если worker опоздал. |
| `shiftDate` | Локальная календарная дата, в которую началось выбранное `ShiftOccurrence`. |

## Точность и преобразования

- PostgreSQL timestamps — `TIMESTAMPTZ(3)`; Java — `Instant`; API принимает ISO-8601 `date-time` со смещением, сохраняет тот же instant в UTC-compatible storage и возвращает UTC timestamp.
- Точная elapsed duration в таблицах/проекциях — integer milliseconds (`BIGINT`). DTO с `durationSec` выражает ту же длительность в секундах согласно своему контракту.
- Enterprise timezone — валидный IANA zone id. Локальные shift boundaries и DST gap/overlap разрешает одна общая политика из `shift-rules.md`.
- Все границы периодов используют `[from,to)`: соседние интервалы могут иметь равную границу, но не пересекаются.
