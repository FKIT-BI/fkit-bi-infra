# Сквозные примеры API

Примеры сокращены до load-bearing полей; точные обязательность и ограничения задаёт OpenAPI.

## Создать и активировать машину

```http
POST /api/v1/enterprises/7b7fdd11-9eb4-46b6-afad-b529ae68ca8f/machines
```

```json
{
  "code": "FLEXO_01",
  "name": "Флексопечать ФП-1",
  "lineId": null,
  "machineType": "FLEXOGRAPHIC_PRESS",
  "inventoryNo": "INV-001",
  "manufacturer": "Example",
  "model": "FP-1000",
  "commissioningYear": 2023,
  "nominalRate": 1200,
  "productionUnit": "METER",
  "sortOrder": null,
  "parameters": []
}
```

После настройки дочерних объектов:

```http
GET /api/v1/machines/05c81626-e0f1-481d-a19d-8bab6ae5a48c/activation-readiness
```

```json
{
  "machineId": "05c81626-e0f1-481d-a19d-8bab6ae5a48c",
  "ready": true,
  "errors": [],
  "warnings": [
    {
      "code": "SCRAP_SIGNAL_NOT_CONFIGURED",
      "message": "Quality и OEE будут недоступны"
    }
  ],
  "checkedAt": "2026-10-08T18:00:00Z"
}
```

```http
PUT /api/v1/machines/05c81626-e0f1-481d-a19d-8bab6ae5a48c/status
```

```json
{ "status": "ACTIVE" }
```

## Настроить правило DOWN

```json
{
  "defaultState": "IDLE",
  "offlineAfterMs": 60000,
  "rules": [
    {
      "name": "Аварийный сигнал",
      "priority": 100,
      "targetState": "DOWN",
      "enterCondition": {
        "type": "COMPARE",
        "signalId": "71f56d16-2ec4-4436-a153-c8fa6b3f2e3b",
        "operator": "EQ",
        "value": true
      },
      "exitCondition": {
        "type": "COMPARE",
        "signalId": "71f56d16-2ec4-4436-a153-c8fa6b3f2e3b",
        "operator": "EQ",
        "value": false
      },
      "activationDelayMs": 5000,
      "releaseDelayMs": 10000
    }
  ]
}
```

Сначала тот же body можно отправить в `/state-configuration/validate`, затем сохранить через `PUT /state-configuration`.

## Открыть карточку машины

Первый экран выполняет два независимых запроса:

```http
GET /api/v1/machines/05c81626-e0f1-481d-a19d-8bab6ae5a48c/operations/current
GET /api/v1/analytics/summary?scope=MACHINE&scopeId=05c81626-e0f1-481d-a19d-8bab6ae5a48c&from=2026-09-08T00:00:00Z&to=2026-10-08T00:00:00Z&compare=PREVIOUS_PERIOD
```

Первый ответ обновляется polling и не зависит от historical range. Второй содержит current/previous periods и не подменяет текущее состояние машины.

## Хронометраж всех смен даты

```http
GET /api/v1/machines/05c81626-e0f1-481d-a19d-8bab6ae5a48c/chronometry?shiftDate=2026-10-08
```

Ответ возвращает `occurrences[]` в порядке `Shift.sortOrder, code`. Чтобы открыть одну смену, frontend добавляет реальный UUID `shiftId`; системных `day/night` нет.

## Зарегистрировать причину для интервала

```http
POST /api/v1/machines/05c81626-e0f1-481d-a19d-8bab6ae5a48c/incidents
```

```json
{
  "from": "2026-10-08T09:10:00Z",
  "to": "2026-10-08T09:25:00Z",
  "stateOverride": null,
  "lossReasonId": "f38455ec-7765-47d0-9ca1-d29b27b718fa",
  "comment": "Ожидание материала",
  "author": "Оператор демо"
}
```

Ответ подтверждает сохранение incident, но aggregates могут оставаться прежними до фоновой публикации. Frontend показывает `recalculating` и poll затронутого read model.

## Пересчитать всю историю текущими правилами

```http
POST /api/v1/machines/05c81626-e0f1-481d-a19d-8bab6ae5a48c/state-recalculations
```

```json
{ "scope": "ALL" }
```

Backend отвечает `202` и job с `PENDING`; frontend poll выполняет по URI из `Location`. До `SUCCEEDED` аналитика продолжает читать предыдущую committed projection.
