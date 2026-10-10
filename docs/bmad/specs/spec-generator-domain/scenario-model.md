# Модель GenerationScenario

## Владение и хранение

`GenerationScenario` принадлежит одному Enterprise и сохраняется в общей PostgreSQL. Один Scenario может включать несколько машин из разных линий только этого предприятия. ProductionLine не является target: она используется для навигации и readiness машины.

| Поле | Тип | Правило |
|---|---|---|
| `id` | UUID | Внутренний идентификатор |
| `enterpriseId` | UUID | Неизменяемый владелец |
| `code` | string | Предлагает frontend; уникален внутри Enterprise и неизменяем |
| `name` | string | Обязательное отображаемое имя |
| `description` | string/null | Необязательное описание |
| `status` | `ACTIVE|DISABLED` | Новый Scenario создаётся `DISABLED` |
| `cycleMode` | `ONCE|LOOP` | Поведение после последней phase |
| `machineTargets` | array | Уникальные Machine и их optional `baseBehaviors` |
| `phases` | array | Упорядоченные phases с компактными behavior overrides |
| `createdAt`, `updatedAt` | instant | Служебные timestamps |

Scenario definition может храниться как валидированный JSONB рядом с индексируемыми identity/status полями. Phase и signal behavior не требуют самостоятельного CRUD: create/update заменяет согласованный definition целиком в одной транзакции.

`machineTargets[].baseBehaviors` задаёт обычное поведение сигналов машины. Оно не обязано включать каждый Signal: отсутствие base означает, что Signal по умолчанию не генерируется.

## Phase

Каждая phase содержит:

- уникальный внутри Scenario `code`;
- `name`;
- положительный `durationMs`;
- необязательный `expectedState` из каталога `RUN|IDLE|DOWN|SETUP|PLANNED_STOP|OFFLINE`;
- компактные `behaviorOverrides` выбранных сигналов.

`expectedState` используется только для диагностики и golden datasets. Generator не записывает его в raw и не гарантирует состояние напрямую: StateRules Analytics должны вывести его из сигналов.

Override имеет `signalId` и одно действие:

- `REPLACE` — полная behavior configuration для этой phase;
- `DISABLE` — measurement сигнала в этой phase отсутствует.

Отсутствующий override использует base behavior; если base также отсутствует, Signal не генерируется. Частичного merge параметров и многоуровневого наследования нет. При создании Run backend разворачивает base плюс overrides в полную effective behavior matrix и сохраняет её в snapshot.

`ONCE` завершает bounded Run после одной последовательности phases. `LOOP` повторяет их до `eventTo` или команды stop; unbounded realtime Run с `ONCE` завершается после последней phase.

## Validation и status

Неполный Scenario разрешено сохранять только как `DISABLED`. Отдельная validation возвращает ошибки и warnings без изменения status. Для `ACTIVE` и нового Run обязательны:

- Enterprise существует и `ACTIVE`;
- каждая Machine принадлежит Enterprise, назначена линии и `ACTIVE`;
- линия каждой Machine `ACTIVE`;
- machine targets уникальны;
- Signal принадлежит target Machine, `ACTIVE` и совместим с behavior model;
- `generationIntervalMs >= 1000`;
- phases имеют уникальные codes, положительную duration и после разрешения base/overrides хотя бы одно генерируемое поведение;
- все numeric/model parameters конечны и проходят границы модели.

Отключение Scenario запрещает новые Runs, но не останавливает уже выполняющийся Run. Физическое удаление отсутствует.

## Обновление и snapshot

Scenario не имеет истории версий. Update заменяет current definition, повторно валидирует его и обновляет `updatedAt`. Run creation читает согласованную current definition и equipment configuration и сохраняет самостоятельный snapshot; дальнейшие изменения Scenario или equipment на этот Run не влияют.
