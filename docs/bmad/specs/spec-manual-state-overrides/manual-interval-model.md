# Модель ручного интервала

## ManualIncident state override

| Поле | Обязательность | Изменяемость | Правило |
| --- | --- | --- | --- |
| `id` | Да | Нет | UUID генерируется backend |
| `machineId` | Да | Нет | Владелец interval |
| `from` | Да | Да | UTC instant, не раньше `machine.coverageFrom`, не в будущем |
| `to` | Нет | Да | UTC instant строго больше `from` и не позже текущего времени; `null` означает ongoing |
| `stateOverride` | Условно | Да | Только `SETUP`, `PLANNED_STOP` или `null` |
| `lossReasonId` | Условно | Да | ACTIVE LossReason того же Enterprise либо `null` |
| `comment` | Нет | Да | Пользовательское пояснение |
| `author` | Нет | Нет | Непроверенное display value до 100 символов |
| `createdAt`, `updatedAt` | Да | Нет | UTC technical timestamps |
| `cancelledAt` | Нет | Только cancel | Soft cancellation |

Интервал полуоткрытый `[from,to)`. Он может пересекать shift boundaries: effective projection и buckets сами разрезают длительность по сменам.

Хотя бы одно из `stateOverride/lossReasonId` обязательно. На одной Machine два incidents с `stateOverride` не могут пересекаться; отдельно не могут пересекаться два incidents с `lossReasonId`. State-only и reason-only intervals могут пересекаться.

## Commands

```text
POST /api/machines/{machineId}/incidents
PUT  /api/incidents/{incidentId}
PUT  /api/incidents/{incidentId}/close
DELETE /api/incidents/{incidentId}
GET  /api/machines/{machineId}/incidents?from=...&to=...
```

Create и update полностью проверяют coverage, время, state enum, reason owner/status и оба вида overlaps одной транзакцией. Update не меняет `id`, `machineId` и `author`. Close устанавливает `to`; повтор close с тем же значением идемпотентен. DELETE идемпотентно устанавливает `cancelledAt` и создаёт dirty range.

Future scheduling, restore cancelled incident и полный audit остаются вне MVP. Полный unified incident contract находится в `spec-loss-reasons-incidents`.
