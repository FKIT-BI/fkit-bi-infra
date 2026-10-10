# Модель телеметрического сигнала

## Граница сущности

`TelemetrySignal` описывает значение, которое может поступать от машины. Он всегда принадлежит одной `Machine`, может ссылаться на один `Component` той же машины, а отсутствие `componentId` означает сигнал уровня машины.

`TelemetryMeasurement` не является частью конфигурационной сущности: это отдельный неизменяемый факт с `signalId`, event time и типизированным значением.

## Поля

| Поле | Обязательность | Изменяемость | Правило MVP |
| --- | --- | --- | --- |
| `id` | Да | Нет | UUID генерируется backend |
| `machineId` | Да | Нет | Владелец сигнала |
| `componentId` | Нет | Да | Только Component той же Machine; `null` означает уровень машины |
| `code` | Да | Нет | Стабильный код, уникальный внутри Machine |
| `name` | Да | Да | Отображаемое имя |
| `description` | Нет | Да | Краткое пользовательское описание |
| `valueType` | Да | До первого raw | `DOUBLE`, `LONG`, `BOOLEAN` или `STRING` |
| `signalKind` | Да | До первого raw | `GAUGE`, `COUNTER` или `STATE` |
| `semanticCode` | Да | До первого raw | Стандартный либо `CUSTOM` |
| `customSemanticCode` | Условно | До первого raw | Требуется только при `semanticCode=CUSTOM` |
| `unitCode` | Нет | До первого raw | Стабильный код единицы; `null` для безразмерных и категориальных значений |
| `expectedIntervalMs` | Нет | Да | Положительный ожидаемый интервал источника |
| `staleAfterMs` | Нет | Да | Положительный порог устаревания последнего значения |
| `validMin` | Нет | Да | Нижняя физически допустимая граница числового сигнала |
| `validMax` | Нет | Да | Верхняя физически допустимая граница числового сигнала |
| `featured` | Да | Да | Показывать сигнал в компактной операционной карточке; default `false` |
| `displayOrder` | Нет | Да | Неотрицательный порядок отображения; затем сортировка по `code` |
| `status` | Да | Да | `ACTIVE` или `DISABLED` |
| `createdAt`, `updatedAt` | Да | Нет | Технические UTC timestamps ответа |

Код предлагает frontend; backend проверяет формат, уникальность и неизменяемость. `customSemanticCode` должен иметь тот же стабильный формат и не может быть пустым. При заданных обоих freshness-полях выполняется `staleAfterMs >= expectedIntervalMs`.

`validMin/validMax` допустимы только для `DOUBLE` и `LONG`, причём `validMin <= validMax`. Выход raw-значения за диапазон не удаляет и не отклоняет факт: ingestion сохраняет его с соответствующим качеством.

## Тип значения и поведение

| `signalKind` | Допустимые `valueType` | Интерпретация |
| --- | --- | --- |
| `GAUGE` | `DOUBLE`, `LONG` | Мгновенное измерение; применимы min, max, sum, count, avg, first и last |
| `COUNTER` | `DOUBLE`, `LONG` | Накопительный счётчик; основная производная — delta с учётом будущего правила reset |
| `STATE` | `BOOLEAN`, `LONG`, `STRING` | Дискретное значение; значимы last и длительность каждого состояния |

`valueType` задаёт физическое представление одного raw-значения. `signalKind` задаёт смысл последовательности и набор допустимых агрегатов.

## Семантический каталог

Начальный набор стандартных кодов:

```text
TEMPERATURE       PRESSURE          FLOW_RATE
LEVEL             HUMIDITY          ROTATIONAL_SPEED
LINEAR_SPEED      VIBRATION         VOLTAGE
CURRENT           POWER             ENERGY
TORQUE            FORCE             POSITION
DISTANCE          PRODUCTION_COUNT  SCRAP_COUNT
CYCLE_COUNT       OPERATING_FLAG    READY_FLAG
ALARM_FLAG        MACHINE_MODE      QUALITY_CODE
LOAD_PERCENT      CUSTOM
```

В API `semanticCode` является строкой, а не закрытым OpenAPI enum. Backend проверяет его по расширяемому каталогу. При `CUSTOM` отдельный `customSemanticCode` фиксирует устойчивое прикладное значение; отображаемое имя не используется как идентификатор семантики.

`unitCode` также является стабильным кодом каталога. Диапазоны нормальной работы, предупреждений и аварий не кодируются через `validMin/validMax`: они принадлежат правилам аналитики. Распределения и диапазоны генерируемых значений принадлежат сценарию generator.

## Жизненный цикл

Всегда неизменяемы `id`, `machineId` и `code`. После первого raw-измерения блокируются `valueType`, `signalKind`, `semanticCode`, `customSemanticCode` и `unitCode`; изменение физического смысла требует нового сигнала и перевода старого в `DISABLED`.

`componentId` можно заменить или очистить только в пределах той же машины. Поскольку история структуры в MVP не версионируется, чтение старых данных использует текущую привязку сигнала к компоненту.

`DISABLED` сохраняет конфигурацию, raw и агрегаты, но исключает сигнал из новых generator runs и новых правил. Отключение сигнала, referenced текущей StateConfiguration активной Machine, отклоняется с `409 SIGNAL_USED_BY_ACTIVE_STATE_CONFIG`. Для отключённой Machine оно разрешено, после чего readiness не позволит активацию до исправления правил или сигнала. Активный generator run продолжает работать по собственному snapshot. Физическое удаление через пользовательский API отсутствует.

`featured` и `displayOrder` влияют только на presentation read models. `LOAD_PERCENT` выбирается явно; backend не выводит semanticCode из имени, кода или единицы сигнала.

## Конфигурационный API

```text
GET  /api/machines/{machineId}/telemetry-signals
POST /api/machines/{machineId}/telemetry-signals
GET  /api/telemetry-signals/{signalId}
PUT  /api/telemetry-signals/{signalId}
PUT  /api/telemetry-signals/{signalId}/status
```

Список поддерживает фильтры `componentId` и `status`. Создание и изменение выполняют полную атомарную валидацию; endpoint изменения не меняет `id`, `machineId`, `code` или заблокированные смысловые поля.
