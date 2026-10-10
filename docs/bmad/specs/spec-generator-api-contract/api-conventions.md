# Конвенции Generator API

- OpenAPI 3.1, JSON `camelCase`, UUID `format: uuid`, timestamps ISO 8601 `date-time` с offset.
- Все event-time ranges полуоткрытые `[from,to)` и сохраняются как UTC instants.
- Resource возвращается напрямую; Scenario list использует `items/page/size/totalElements/totalPages`, Run journal — `items/nextCursor`.
- Create/update/response DTO разделены. `PUT` полностью заменяет изменяемое Scenario definition; явный `null` очищает optional field.
- Scenario create получает `201`; Run create/retry и running stop — `202`; side-effect-free validate получает `200` даже при `valid=false`.
- `POST /runs` требует `Idempotency-Key`: same key/body возвращает исходный Run, changed body получает `409 IDEMPOTENCY_KEY_REUSED`.
- Empty valid collection возвращает `200` с пустым `items`; отсутствующий addressed resource — `404`.
- `400` означает malformed/несовместимый transport input, `409` — state/overlap/idempotency conflict, `422` — полный набор domain validation issues, `500` — unexpected error с `traceId`.
- `ErrorResponse`: `code`, `message`, `traceId`, `fieldErrors[]`, `details`.
- Field path использует JSON-путь request, например `machineTargets[0].baseBehaviors[2].parameters.mean`.
- Все публичные операции требуют OpenAPI `bearerAuth` (JWT); роли/RBAC не вводятся. Display actors не являются RBAC roles; выпуск и bootstrap credentials находятся вне Generator resource API.
- Frontend client генерируется из OpenAPI; transport DTO не используются как persistence, execution или telemetry models.
