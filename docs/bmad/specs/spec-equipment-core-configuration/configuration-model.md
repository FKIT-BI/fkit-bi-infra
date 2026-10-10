# Модель и потоки базовой конфигурации

## Enterprise

| Поле | Обязательность | Изменяемость | Правило MVP |
| --- | --- | --- | --- |
| `id` | Да | Нет | UUID генерируется backend |
| `code` | Да | Нет | Глобально уникальный стабильный код |
| `name` | Да | Да | Отображаемое имя; повторения разрешены |
| `timezone` | Да | Ограниченно | IANA ZoneId; блокируется после появления временных эксплуатационных данных |
| `status` | Да | Да | Собственный `ACTIVE` или `DISABLED`; по умолчанию `ACTIVE` |
| `createdAt`, `updatedAt` | Да | Нет | Технические UTC timestamps ответа |

Одно развёртывание поддерживает несколько предприятий. `Shift` принадлежит предприятию, но создаётся отдельным ресурсом. Изменение `timezone` возвращает `409 ENTERPRISE_TIMEZONE_LOCKED`, если у предприятия уже существуют телеметрия, инциденты, запуски генератора или рассчитанная аналитика.

Команды:

```text
POST /api/enterprises
GET  /api/enterprises
GET  /api/enterprises/{enterpriseId}
PUT  /api/enterprises/{enterpriseId}
PUT  /api/enterprises/{enterpriseId}/status
```

## ProductionLine

| Поле | Обязательность | Изменяемость | Правило MVP |
| --- | --- | --- | --- |
| `id` | Да | Нет | UUID генерируется backend |
| `enterpriseId` | Да | Нет | Обязательный владелец |
| `code` | Да | Нет | Уникален внутри предприятия |
| `name` | Да | Да | Отображаемое имя; повторения разрешены |
| `sortOrder` | Да | Да | Неотрицательное целое; повторения разрешены |
| `status` | Да | Да | Собственный `ACTIVE` или `DISABLED`; по умолчанию `ACTIVE` |
| `createdAt`, `updatedAt` | Да | Нет | Технические UTC timestamps ответа |

Если `sortOrder` не передан при создании, backend назначает `max(sortOrder) + 10`, начиная с `10`. Чтение сортирует по `sortOrder ASC, code ASC`. Отдельная пакетная перестановка в MVP не требуется: позиция меняется обычным обновлением линии.

Отключение линии не изменяет статусы машин и не удаляет историю. Активный generator run продолжает работу по снимку и его телеметрия рассчитывается; новый run через отключённую линию запрещён. Конфигурацию внутри отключённой линии разрешено редактировать.

Команды:

```text
GET  /api/enterprises/{enterpriseId}/lines
POST /api/enterprises/{enterpriseId}/lines
GET  /api/lines/{lineId}
PUT  /api/lines/{lineId}
PUT  /api/lines/{lineId}/status
```

## Machine

| Поле | Обязательность | Изменяемость | Правило MVP |
| --- | --- | --- | --- |
| `id` | Да | Нет | UUID генерируется backend |
| `enterpriseId` | Да | Нет | Прямой обязательный владелец |
| `lineId` | Нет | Однократно | Допустим только переход `null → Line` того же предприятия |
| `code` | Да | Нет | Уникален внутри предприятия |
| `name` | Да | Да | Отображаемое имя |
| `machineType` | Нет | Да | Свободная строка только для отображения и фильтрации |
| `inventoryNo` | Нет | Да | При наличии уникален внутри предприятия |
| `manufacturer` | Нет | Да | Производитель для паспорта; не участвует в аналитике |
| `model` | Нет | Да | Модель оборудования для паспорта; не определяет поведение |
| `commissioningYear` | Нет | Да | Четырёхзначный год ввода в эксплуатацию |
| `nominalRate` | Нет | Да | Положительное число выпуска за час; задаётся вместе с `productionUnit` |
| `productionUnit` | Нет | Да | Единица выпуска, совместимая с выходным сигналом |
| `sortOrder` | Нет | Да | `null` без линии; порядок внутри назначенной линии |
| `status` | Да | Да | При создании всегда `DISABLED` |
| `parameters` | Нет | Да | До 100 встроенных типизированных display-параметров |
| `createdAt`, `updatedAt` | Да | Нет | Технические UTC timestamps ответа |

Если пара `nominalRate` и `productionUnit` отсутствует, показатель `performance` равен `null`. До назначения линии машина может получать компоненты, сигналы и правила, но не используется генератором, telemetry ingestion и аналитикой.

Обычный `Machine` update атомарно изменяет `name`, `machineType`, `inventoryNo`, `manufacturer`, `model`, `commissioningYear`, пару `nominalRate`/`productionUnit`, `sortOrder` и `parameters`. `id`, `enterpriseId`, `code`, `lineId` и `status` этим запросом не меняются.

## Типизированные display-параметры

`Machine.parameters` и `Component.parameters` являются встроенным списком, а не самостоятельными сущностями:

| Поле | Правило |
| --- | --- |
| `code` | Обязательный стабильный код, уникальный внутри владельца |
| `name` | Обязательное отображаемое имя |
| `valueType` | `STRING`, `NUMBER` или `BOOLEAN` |
| `value` | JSON scalar строго соответствующего типа |
| `unitCode` | Допустим только для `NUMBER`; для остальных отсутствует |
| `sortOrder` | Неотрицательное целое; затем сортировка по `code` |

На одного владельца допускается не более 100 параметров. Список целиком заменяется вместе с обычным update владельца и хранится как валидированный JSONB. Параметры предназначены для паспорта и отображения: StateRules, формулы, фильтры аналитики и generator logic на них не ссылаются.

Команды:

```text
POST /api/enterprises/{enterpriseId}/machines
GET  /api/enterprises/{enterpriseId}/machines
GET  /api/enterprises/{enterpriseId}/machines?assignment=UNASSIGNED
GET  /api/lines/{lineId}/machines
GET  /api/machines/{machineId}
PUT  /api/machines/{machineId}
PUT  /api/machines/{machineId}/status
```

Создание принимает необязательный `lineId`, поэтому один контракт поддерживает как свободную, так и сразу назначенную машину. Если `sortOrder` не передан для назначенной машины, backend использует `max(sortOrder) + 10`.

## Назначение машин линии

```text
POST /api/lines/{lineId}/machine-assignments
```

```json
{
  "machineIds": [
    "4af46cea-4b97-4733-9124-a99b4de34867",
    "2ecaf2cf-5111-45d9-ac90-dde217f4543a"
  ]
}
```

Backend в одной транзакции проверяет существование линии и машин, совпадение `enterpriseId`, отсутствие повторяющихся идентификаторов и `lineId = null` у каждой машины. Порядок входного массива определяет автоматически назначаемые значения `sortOrder` с шагом `10` после текущего максимума линии.

Любое нарушение возвращает `409` с перечнем конфликтов и не изменяет ни одну машину. Для уже назначенной машины ошибка содержит `machineId`, `machineCode`, `currentLineId` и отображаемое имя текущей линии. Конкурирующие назначения подчиняются тому же правилу: успешно фиксируется не более одной операции.

## Отдельная конфигурация дочерних объектов

Компонент сразу создаётся внутри машины и не проходит отдельную операцию назначения:

```text
POST /api/machines/{machineId}/components
GET  /api/machines/{machineId}/components
PUT  /api/components/{componentId}
PUT  /api/components/{componentId}/status
PUT  /api/components/{componentId}/parent
```

Список компонентов возвращается плоским с `parentComponentId`; frontend строит дерево. `parentComponentId` меняется только внутри той же машины с атомарной проверкой циклов. Сигналы создаются через `POST /api/machines/{machineId}/signals` и могут иметь необязательный `componentId` той же машины.

## Подготовка и активация машины

Нормативная последовательность:

1. Создать `Machine` в `DISABLED`.
2. Назначить `ProductionLine` сразу или позднее.
3. Создать дерево `Component`, если оно требуется.
4. Создать `TelemetrySignal` уровня машины или компонента.
5. Настроить декларативные правила аналитики.
6. Проверить readiness и перевести машину в `ACTIVE` отдельной status-командой.

Проверка активации блокирует переход при отсутствии назначенной активной Line, отключённом Enterprise, невалидной MachineStateConfig, отключённом referenced signal, отсутствующем `staleAfterMs` такого сигнала или структурном конфликте. Отсутствующие `PRODUCTION_COUNT`, `SCRAP_COUNT`, пара `nominalRate/productionUnit` или featured signals являются предупреждениями: они ограничивают показатели или карточку, но не блокируют активацию.

Предварительное чтение readiness и переход в `ACTIVE` используют одну доменную проверку. Status-команда при активации повторяет её атомарно; frontend-проверка не является разрешением на последующее сохранение.

Изменение собственного `status` Enterprise, ProductionLine или Machine не каскадирует и не меняет status потомков. Отключение сохраняет историю и не останавливает активный generator run по snapshot; новый run и readiness отдельно проверяют все требуемые текущие объекты.
