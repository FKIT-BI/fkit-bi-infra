# Каталог операций

## Scenario

| Method | Path | Результат |
|---|---|---|
| `GET` | `/api/v1/scenarios` | Page Scenario по required `enterpriseId`, optional status/search |
| `POST` | `/api/v1/scenarios` | Создать `DISABLED` Scenario, вернуть `201` и validation |
| `POST` | `/api/v1/scenarios/validate` | Проверить несохранённый Scenario input без side effects |
| `GET` | `/api/v1/scenarios/{scenarioId}` | Scenario detail с current validation |
| `PUT` | `/api/v1/scenarios/{scenarioId}` | Полностью заменить изменяемый definition |
| `PUT` | `/api/v1/scenarios/{scenarioId}/status` | `ACTIVE|DISABLED`; activation повторно валидирует equipment |

## GenerationRun

| Method | Path | Результат |
|---|---|---|
| `GET` | `/api/v1/runs` | Cursor journal по enterprise и optional scenario/machine/mode/status/time |
| `POST` | `/api/v1/runs/validate` | Нормализация, estimate, conflicts и validation без создания Run |
| `POST` | `/api/v1/runs` | Создать Run с required `Idempotency-Key`, вернуть `202` и `Location` |
| `GET` | `/api/v1/runs/{runId}` | Detail: lifecycle, progress, counters, failure, analytics context |
| `POST` | `/api/v1/runs/{runId}/stop` | Idempotent cancel/stop, вернуть текущее принятое состояние |
| `POST` | `/api/v1/runs/{runId}/retry` | Retry только `FAILED` с `retryable=true` |

Raw writer, checkpoint mutation, attempt history и equipment queries не являются public operations.
