# Единая модель ManualIncident

## Поля

| Поле | Обязательность | Изменяемость | Правило |
| --- | --- | --- | --- |
| `id` | Да | Нет | UUID backend |
| `machineId` | Да | Нет | Владелец interval |
| `from` | Да | Да | UTC instant, не раньше `coverageFrom` и не позже текущего времени |
| `to` | Нет | Да | Строго больше `from` и не позже текущего времени; `null` означает ongoing |
| `stateOverride` | Условно | Да | `SETUP`, `PLANNED_STOP` или `null` |
| `lossReasonId` | Условно | Да | ACTIVE reason того же Enterprise либо `null` |
| `comment` | Нет | Да | До 500 символов |
| `author` | Нет | Нет | До 100 символов, непроверенное display value |
| `createdAt`, `updatedAt` | Да | Нет | UTC technical timestamps |
| `cancelledAt` | Нет | Только cancel | Soft cancellation |

Хотя бы одно из `stateOverride/lossReasonId` обязательно. Derived response field `effectType` является закрытым Java/OpenAPI enum и не хранится:

```text
stateOverride != null, lossReasonId == null → STATE_OVERRIDE
stateOverride == null, lossReasonId != null → LOSS_ANNOTATION
stateOverride != null, lossReasonId != null → STATE_OVERRIDE_WITH_REASON
```

Интервал полуоткрытый `[from,to)` и может пересекать shift boundaries. Future boundaries запрещены; продолжающийся период задаётся `to=null`. Reason-only create требует `from<dataThrough` и должен пересекать в готовой timeline хотя бы один effective `IDLE`, `DOWN`, `SETUP` или `PLANNED_STOP`; иначе возвращается `409 INCIDENT_HAS_NO_LOSS_INTERVAL`.

Ongoing reason annotation продолжает назначать reason новым eligible intervals по мере публикации. Части RUN/OFFLINE игнорируются. Последующий state recalculation может уменьшить attributed duration до нуля, но incident сохраняется.

## API-направление

```text
GET    /api/machines/{machineId}/incidents
POST   /api/machines/{machineId}/incidents
GET    /api/incidents/{incidentId}
PUT    /api/incidents/{incidentId}
PUT    /api/incidents/{incidentId}/close
DELETE /api/incidents/{incidentId}
```

Update может изменить boundaries/effects/comment, но не `id`, `machineId`, `author`, `createdAt`. Close устанавливает `to`; повтор с тем же значением идемпотентен. DELETE выполняет idempotent soft cancel. List исключает cancelled по умолчанию и поддерживает `includeCancelled=true`.
