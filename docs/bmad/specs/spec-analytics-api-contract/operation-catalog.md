# Каталог операций

## Configuration

| Method | Path | Назначение |
| --- | --- | --- |
| GET, POST | `/api/v1/enterprises` | Page предприятий; создать Enterprise |
| GET, PUT | `/api/v1/enterprises/{enterpriseId}` | Прочитать; заменить изменяемые поля |
| PUT | `/api/v1/enterprises/{enterpriseId}/status` | Изменить собственный status без каскада |
| GET, POST | `/api/v1/enterprises/{enterpriseId}/shifts` | Page смен; создать Shift |
| GET, PUT | `/api/v1/shifts/{shiftId}` | Прочитать; изменить допустимые поля Shift |
| PUT | `/api/v1/shifts/{shiftId}/status` | Изменить status Shift |
| GET, POST | `/api/v1/enterprises/{enterpriseId}/loss-reasons` | Page причин; создать LossReason |
| GET, PUT | `/api/v1/loss-reasons/{lossReasonId}` | Прочитать; изменить display fields/category до использования |
| PUT | `/api/v1/loss-reasons/{lossReasonId}/status` | Включить или отключить причину |
| GET, POST | `/api/v1/enterprises/{enterpriseId}/lines` | Page линий; создать ProductionLine |
| GET, PUT | `/api/v1/lines/{lineId}` | Прочитать; изменить name/sortOrder |
| PUT | `/api/v1/lines/{lineId}/status` | Изменить status линии без каскада |
| GET, POST | `/api/v1/enterprises/{enterpriseId}/machines` | Page машин с assignment/line/status/search; создать Machine с optional lineId |
| GET | `/api/v1/lines/{lineId}/machines` | Page машин выбранной линии |
| GET, PUT | `/api/v1/machines/{machineId}` | Прочитать; заменить изменяемые паспортные поля |
| PUT | `/api/v1/machines/{machineId}/status` | Disable либо activation с повторной readiness validation |
| POST | `/api/v1/lines/{lineId}/machine-assignments` | Атомарно назначить свободные Machines линии |
| GET, POST | `/api/v1/machines/{machineId}/components` | Плоский список дерева; создать Component |
| GET, PUT | `/api/v1/components/{componentId}` | Прочитать; изменить Component без parent/status |
| PUT | `/api/v1/components/{componentId}/parent` | Переместить внутри той же Machine с cycle check |
| PUT | `/api/v1/components/{componentId}/status` | Изменить status без каскада |
| GET, POST | `/api/v1/machines/{machineId}/telemetry-signals` | Page сигналов; создать signal |
| GET, PUT | `/api/v1/telemetry-signals/{signalId}` | Прочитать; изменить допустимые signal fields |
| PUT | `/api/v1/telemetry-signals/{signalId}/status` | Изменить status с rule-reference validation |
| GET, PUT | `/api/v1/machines/{machineId}/state-configuration` | Прочитать или атомарно заменить текущую конфигурацию |
| POST | `/api/v1/machines/{machineId}/state-configuration/validate` | Проверить DTO без сохранения |
| GET | `/api/v1/machines/{machineId}/activation-readiness` | Полный список blocking errors и warnings |

## Navigation and current operations

| Method | Path | Назначение |
| --- | --- | --- |
| GET | `/api/v1/enterprises/{enterpriseId}/equipment-tree` | Компактные Line/Machine identities, own statuses и unassigned group |
| GET | `/api/v1/enterprises/{enterpriseId}/operations/overview` | Current machine cards и state totals для предприятия/optional line |
| GET | `/api/v1/machines/{machineId}/operations/current` | Паспортный header, effective current state и featured current signals |
| GET | `/api/v1/machines/{machineId}/telemetry/current` | Все, featured либо выбранные current signal projections |

## Historical analytics

| Method | Path | Назначение |
| --- | --- | --- |
| GET | `/api/v1/analytics/summary` | Metrics current period и optional previous period для scope |
| GET | `/api/v1/analytics/metrics/timeseries` | Server-aggregated metric points |
| GET | `/api/v1/machines/{machineId}/telemetry/series` | Numeric GAUGE/COUNTER series одного signal |
| GET | `/api/v1/analytics/losses/timeseries` | Loss durations по времени и причинам |
| GET | `/api/v1/analytics/losses/pareto` | Top named reasons плюс UNCLASSIFIED/OTHER |
| GET | `/api/v1/machines/{machineId}/chronometry` | Одна либо все shift occurrences выбранной local date |
| GET | `/api/v1/machines/{machineId}/state-intervals` | Cursor-page effective intervals с фильтрами таблицы |

Общие analytics query fields: `scope`, `scopeId`, `from`, `to`, optional `shiftId`, optional `shiftDate`; series добавляют `resolution`, loss endpoints — `top`. Telemetry series адресует сигнал через UUID `signalId`, а не display code.

## Manual incidents

| Method | Path | Назначение |
| --- | --- | --- |
| GET | `/api/v1/enterprises/{enterpriseId}/incidents` | Общий cursor journal с machine/line/time/effect/reason filters |
| GET, POST | `/api/v1/machines/{machineId}/incidents` | Cursor journal; создать incident для Machine (`POST` требует `Idempotency-Key`) |
| GET, PUT | `/api/v1/incidents/{incidentId}` | Прочитать; изменить boundaries/effects/comment |
| PUT | `/api/v1/incidents/{incidentId}/close` | Idempotently установить конец ongoing incident |
| DELETE | `/api/v1/incidents/{incidentId}` | Idempotent soft cancel |

## Recalculation

| Method | Path | Назначение |
| --- | --- | --- |
| GET, POST | `/api/v1/machines/{machineId}/state-recalculations` | Cursor journal; создать PERIOD или ALL job |
| GET | `/api/v1/state-recalculations/{recalculationId}` | Статус, progress, effective range и error |

## Excluded transport

Raw measurements не имеют public REST endpoint в этом документе. Realtime, historical и scheduled generator use cases управляются отдельным Generator API, а измерения записываются внутренним batch sink с отдельной идемпотентностью.
