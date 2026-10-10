# Модель LossReason

## Поля

| Поле | Обязательность | Изменяемость | Правило |
| --- | --- | --- | --- |
| `id` | Да | Нет | UUID backend |
| `enterpriseId` | Да | Нет | Владелец справочника |
| `code` | Да | Нет | Стабильный код, уникальный внутри Enterprise |
| `name` | Да | Да | Нормализованно уникально внутри Enterprise |
| `description` | Нет | Да | Пользовательское описание |
| `category` | Да | До первого использования | `LossCategory` |
| `color` | Нет | Да | `#RRGGBB`; frontend использует default при `null` |
| `status` | Да | Да | `ACTIVE` или `DISABLED` |
| `createdAt`, `updatedAt` | Да | Нет | UTC technical timestamps |

## LossCategory

Закрытый Java/OpenAPI enum:

```text
EQUIPMENT
MATERIAL
PERSONNEL
PROCESS
QUALITY
CHANGEOVER
EXTERNAL
OTHER
```

В PostgreSQL category хранится как `VARCHAR` с application validation и DB CHECK, а не native PostgreSQL enum. Расширение набора выполняется миграцией приложения и контракта.

Конкретный `LossReason` не является enum: это enterprise-scoped пользовательская строка справочника.

## Жизненный цикл

Новое предприятие начинается с пустого справочника причин потерь. Причины являются предметными настройками предприятия и создаются обычным API; Liquibase и Enterprise create не добавляют tenant-specific defaults. Demo/test данные задаются отдельно от production migrations.

После первого использования `code`, `enterpriseId` и `category` неизменяемы. `name`, `description` и `color` можно исправлять; исторические ответы используют текущие display values, версии не создаются.

`DISABLED` блокирует новое назначение и замену причины на неё. Existing и ongoing incidents продолжают действовать; их boundaries/comment можно исправлять, пока `lossReasonId` не меняется. История доступна, reactivation разрешена. Физического удаления нет.

`isPlanned` отсутствует: плановость выводится из effective state. `UNCLASSIFIED` означает `lossReasonId=null`, а `OTHER` создаётся только аналитическим ответом и не хранится в каталоге.

## API-направление

```text
GET  /api/enterprises/{enterpriseId}/loss-reasons
POST /api/enterprises/{enterpriseId}/loss-reasons
GET  /api/loss-reasons/{lossReasonId}
PUT  /api/loss-reasons/{lossReasonId}
PUT  /api/loss-reasons/{lossReasonId}/status
```

List по умолчанию возвращает ACTIVE и поддерживает явный status filter. Исторические DTO разрешают DISABLED reason.
