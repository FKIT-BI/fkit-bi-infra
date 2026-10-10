# Модель конфигурации состояния

## MachineStateConfig

Для Machine хранится одна текущая конфигурация:

| Поле | Обязательность | Правило |
| --- | --- | --- |
| `machineId` | Да | Владелец и первичный ключ |
| `defaultState` | Да | Default `IDLE`; любое пользовательское состояние кроме `OFFLINE` |
| `offlineAfterMs` | Да | Положительное; default `60_000` |
| `rules` | Да | От 1 до 20 полностью валидных rules |
| `updatedAt` | Да | UTC timestamp последнего атомарного изменения |

Конфигурация хранится как валидированный JSONB-документ в одной строке. Это не неуправляемая EAV-модель: schema закрыта DTO и AST-контрактом. Backend после сохранения компилирует JSON в типизированную внутреннюю модель и кэширует evaluator; processing path не разбирает JSON на каждом measurement.

Версий нет. `PUT` полностью заменяет текущий документ одной транзакцией. Политика перерасчёта уже опубликованных исторических интервалов определяется отдельно.

## StateRule

| Поле | Обязательность | Правило |
| --- | --- | --- |
| `id` | Да | UUID правила внутри конфигурации |
| `name` | Да | Отображаемое имя |
| `priority` | Да | Уникальное целое внутри Machine; большее значение выше |
| `targetState` | Да | `RUN`, `IDLE`, `DOWN`, `PLANNED_STOP` или `SETUP` |
| `enterCondition` | Да | Валидный condition AST |
| `exitCondition` | Нет | Валидный AST; отсутствие использует инверсию результата enter |
| `activationDelayMs` | Да | Неотрицательная длительность непрерывного TRUE |
| `releaseDelayMs` | Да | Неотрицательная длительность непрерывного выхода |

Rule ID сохраняется при редактировании существующего правила; для нового правила backend может сгенерировать UUID и вернуть нормализованный документ.

## Machine activation

Переход Machine в `ACTIVE` требует:

- существующую валидную MachineStateConfig;
- хотя бы одно rule;
- положительный `offlineAfterMs`;
- существование всех referenced signals на этой Machine;
- `staleAfterMs` у каждого referenced signal;
- корректное соответствие literal и `TelemetrySignal.valueType`.

## API

```text
GET  /api/machines/{machineId}/state-configuration
PUT  /api/machines/{machineId}/state-configuration
POST /api/machines/{machineId}/state-configuration/validate
```

`validate` применяет все проверки `PUT`, но ничего не сохраняет. Ошибки содержат machine/rule ID, JSON path, код и сообщение; один ответ может вернуть все независимо обнаруженные ошибки.
