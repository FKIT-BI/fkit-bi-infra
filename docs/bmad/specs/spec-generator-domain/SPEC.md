---
id: SPEC-generator-domain
companions:
  - scenario-model.md
  - signal-behavior-models.md
  - run-model.md
sources: []
---

> **Canonical contract.** Этот SPEC и файлы из `companions:` составляют полный контракт базового домена generator для Scenario, raw-signal behavior и GenerationRun.

# Домен генератора сырых сигналов

## Why

Пользователю нужно воспроизводимо эмулировать работу уже настроенного оборудования в realtime, прошлом и будущем, чтобы демонстрировать и проверять аналитику. Generator должен использовать единую производственную структуру, не создавать конкурирующий каталог оборудования и не подменять рассчитанные состояния машины готовыми ответами.

## Capabilities

- **CAP-1**
  - **intent:** Пользователь может сохранить переиспользуемый сценарий предприятия для одной или нескольких существующих машин.
  - **success:** `GenerationScenario` имеет стабильный код и `ACTIVE|DISABLED`, ссылается только на машины одного Enterprise и не дублирует equipment CRUD.

- **CAP-2**
  - **intent:** Пользователь может постепенно настроить Scenario и проверить его готовность перед запуском.
  - **success:** Неполный Scenario сохраняется как `DISABLED`, а activation/run возвращают точные validation issues для ownership, line assignment, statuses, signals и несовместимых behavior types.

- **CAP-3**
  - **intent:** Пользователь может описать последовательность режимов поведения исходных сигналов.
  - **success:** Scenario выполняет ordered phases и согласованные numeric, counter, boolean и string/state models с интервалом не менее 1000 ms.

- **CAP-4**
  - **intent:** Каждый запуск можно объяснить и воспроизвести после изменения текущей конфигурации.
  - **success:** `GenerationRun` сохраняет immutable snapshot Scenario, оборудования и сигналов вместе с deterministic random seed.

- **CAP-5**
  - **intent:** Пользователь может наблюдать и управлять жизненным циклом запуска.
  - **success:** `SCHEDULED`, `QUEUED`, `RUNNING`, `STOP_REQUESTED`, `COMPLETED`, `STOPPED`, `CANCELLED` и `FAILED` имеют однозначные переходы и terminal semantics.

- **CAP-6**
  - **intent:** Generator предотвращает конфликтующие запуски и сохраняет ресурсы минимального стенда.
  - **success:** Машина не участвует одновременно в двух realtime executions, future reservations не пересекаются, multi-machine start атомарен, а historical execution на стенде 4 vCPU/8 GB только один.

- **CAP-7**
  - **intent:** Generator публикует исходные факты, из которых Analytics самостоятельно получает состояния и показатели.
  - **success:** Каждый measurement содержит существующий `signalId`, `observedAt` и одно типизированное value; официальный `MachineState` в telemetry не передаётся.

## Constraints

- Enterprise, ProductionLine, Machine, Component и TelemetrySignal создаются и изменяются только через Analytics API.
- Frontend получает equipment selection из Analytics API; Generator API не предоставляет альтернативный equipment CRUD.
- Generator читает текущую equipment configuration из общей PostgreSQL, но записывает только собственный домен и append-only raw telemetry.
- Scenario, Run, snapshot, progress и terminal result являются durable PostgreSQL data; миграциями общей базы владеет `fkit-bi-analytics`.
- Scenario не версионируется; изоляция запуска обеспечивается snapshot.
- Одноразовый будущий запуск моделируется `SCHEDULED` Run; отдельная recurring Schedule entity отсутствует.
- Scenario использует один уровень `baseBehaviors + REPLACE|DISABLE overrides`; Run snapshot хранит уже развёрнутую effective behavior matrix.
- Точная модель Scenario описана в `scenario-model.md`, каталог сигналов — в `signal-behavior-models.md`, lifecycle и concurrency — в `run-model.md`.

## Non-goals

- Создание или редактирование производственной структуры внутри Generator API.
- Запись готового состояния машины, агрегатов, инцидентов или KPI.
- Повторяющиеся календарные расписания.
- История версий Scenario и machine configuration.
- Частота генерации выше 1 Hz и waveform payload.
- Полная физическая модель промышленного оборудования в первой реализации.

## Success signal

Пользователь выбирает существующие активные машины, сохраняет и валидирует многофазный Scenario, создаёт Run, а generator воспроизводимо записывает типизированные raw measurements по snapshot; Analytics независимо выводит ожидаемые состояния и показатели без дублирования equipment model.
