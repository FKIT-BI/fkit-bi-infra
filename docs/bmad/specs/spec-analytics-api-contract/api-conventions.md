# Конвенции Analytics API

## Версия и представление

- Base path: `/api/v1`.
- JSON использует `camelCase`; UUID передаются как `format: uuid`.
- Instant передаётся как ISO 8601 UTC `date-time`; локальная дата смены — `date`; локальная граница расписания — `HH:mm` без offset.
- Все временные диапазоны полуоткрытые `[from,to)`.
- Resource response возвращается напрямую. Collection response использует `items` и page либо cursor metadata.
- Create, update и response DTO не переиспользуются как один двунаправленный объект.

## Команды и изменяемость

- `POST` создаёт ресурс и возвращает `201` с `Location`.
- `PUT /{id}` полностью заменяет набор изменяемых полей; optional поле очищается явным `null`.
- `PUT /{id}/status` меняет только собственный `ACTIVE/DISABLED`; каскада нет.
- Configuration collection без `status` возвращает только `ACTIVE`; явный `status=DISABLED` нужен для редактирования/восстановления. Operational selectors показывают только `ACTIVE`; detail и историческое чтение по ID остаются доступны для отключённых ресурсов.
- Структурные действия (`parent`, `machine-assignments`, readiness, validate, close) имеют отдельные endpoints.
- Пользовательского физического DELETE конфигурации нет. `DELETE /incidents/{id}` является idempotent soft cancel.
- Общий `Idempotency-Key` для configuration create в MVP отсутствует. Уникальность `code` детерминированно защищает от повторного логического создания.
- `POST /machines/{machineId}/incidents` требует `Idempotency-Key` длиной 8–128 символов; область — authenticated user + operation. Тот же key/body возвращает исходный успешный ответ, тот же key с иным body возвращает `409 IDEMPOTENCY_KEY_REUSED`.

## Фильтрация и pagination

- Configuration tables используют zero-based `page`, `size` default 50 max 200 и документированный `sort`.
- Tree и bounded catalog lists возвращаются целиком только там, где response специально компактен.
- Incidents, state intervals и recalculation journal используют opaque `cursor`, `limit` default 100 max 500 и стабильную сортировку по времени плюс UUID.
- Timeseries не paginate: backend выбирает либо проверяет resolution и возвращает полный bounded ряд.
- Повторяемые filters кодируются повторяемым query parameter либо comma-separated только там, где это явно задано OpenAPI.

## Исторический контекст

Historical endpoints принимают один из режимов:

1. `from + to`, опционально `shiftId` для фильтра occurrences этой Shift внутри диапазона.
2. `shiftId + shiftDate` для одного occurrence; `from/to` тогда отсутствуют.

Литералы `all`, `day`, `night` не являются системными shift identifiers. Общий запрос не передаёт `shiftId`. Максимальная исходная длительность — 90 дней.

## Актуальность

Historical envelope содержит `requestedFrom`, `requestedTo`, `actualFrom`, `actualTo`, `dataThrough`, `calculatedAt`, `partial`, `recalculating` и применённую `resolution`, когда она имеет смысл.

Current response использует:

- `freshness` для конкретного сигнала (`NO_DATA`, `FRESH`, `STALE`);
- `stale` для отставания проекции относительно SLO;
- `recalculating` для готовящейся атомарной замены;
- `dataThrough` как исключительную границу опубликованной истории.

Пустой корректный результат возвращает `200` и пустой `items/points`; отсутствие ресурса возвращает `404`.

## Ошибки

Единый `ErrorResponse` содержит:

```text
code, message, traceId, fieldErrors[], details
```

`fieldErrors[]` содержит `path`, стабильный `code` и `message`. `details` хранит структурированные identifiers и конфликтующие границы, но клиентская логика опирается на `code`, не на текст.

| HTTP | Значение |
| --- | --- |
| `400` | malformed JSON/query или несовместимый набор query parameters |
| `404` | адресуемый ресурс отсутствует |
| `409` | конфликт состояния, ownership, overlap, immutable/locked поле или активный job |
| `422` | ошибки полей либо декларативной конфигурации, которые можно показать вместе |
| `500` | непредвиденная серверная ошибка с `traceId` |

## Асинхронные изменения

Incident mutation и recalculation не заставляют HTTP ждать аналитический pipeline. До атомарной публикации reads возвращают предыдущий полный результат с `recalculating=true`. `POST state-recalculations` возвращает `202`; configuration mutations возвращают сохранённый ресурс после транзакционной проверки.

## Authentication boundary

Все Analytics business operations требуют JWT Bearer из `Authorization`. Auth endpoints не входят в этот OpenAPI и описаны отдельно в `fkit-bi-infra/docs/contracts/auth-api.yaml`; там login является публичным исключением. Analytics выпускает общий JWT `HS256` для `fkit-bi-api` на 30 минут; Generator только валидирует его. Refresh token вне MVP. Все обычные аутентифицированные пользователи равноправны; единственное исключение — bootstrap-user может создавать учётные записи. Названия «оператор» и «аналитик» описывают user flows, а не роли. Authentication не меняет resource identifiers или бизнес DTO.

## Generated boundaries

- Frontend генерирует типизированный HTTP client из OpenAPI и не поддерживает параллельные handwritten transport types.
- Backend может генерировать Spring controller interfaces и transport DTO, но вручную отображает их в application/domain models.
- Generated DTO не используются как JPA entities, calculation models или SQL records.
- Business error codes, domain validation и mapping nullable semantics реализуются backend и проверяются contract tests.
- Изменение OpenAPI сначала проходит lint и совместимость generated clients, затем используется реализацией.
