# Семантика DTO

## Configuration identity

Каждый самостоятельный configuration response содержит `id`, `code`, `name`, `status`, `createdAt`, `updatedAt` плюс owner-specific fields. `id` и owner IDs генерирует backend; create принимает `code`, update его не принимает.

`StatusUpdate` содержит только `status: ACTIVE|DISABLED`. Machine create всегда даёт `DISABLED`, Enterprise/Line/Shift/LossReason/Component/TelemetrySignal по умолчанию `ACTIVE`, если status не является отдельным обязательным решением create DTO.

## Passport parameters

Machine имеет явные `machineType`, `inventoryNo`, `manufacturer`, `model`, `commissioningYear`, `nominalRate`, `productionUnit`. Machine и Component дополнительно принимают до 100 `parameters` с discriminator `valueType`:

```text
STRING  -> code, name, value:string, sortOrder
NUMBER  -> code, name, value:number, unitCode?, sortOrder
BOOLEAN -> code, name, value:boolean, sortOrder
```

`code` уникален внутри владельца. Эти параметры предназначены для паспорта и не участвуют в StateRules, формулах или аналитических filters.

## State configuration

`MachineStateConfig` содержит `defaultState`, положительный `offlineAfterMs` и 1..20 rules. Rule содержит UUID, name, unique priority, targetState кроме OFFLINE, `enterCondition`, optional `exitCondition`, non-negative activation/release delays.

Condition AST использует discriminator `type`: `ALL`, `ANY`, `NOT`, `COMPARE`. Compare использует `signalId` и `EQ|NE|GT|GTE|LT|LTE|BETWEEN|IN` с типизированным operand. Лимиты: depth 10, 100 nodes, IN до 50 unique literals. `validate` возвращает normalized config и все independently found errors.

## Current read models

Current signal возвращает metadata конфигурации, last received и last usable typed values, observed/received timestamps, source quality, validation flags, computed `freshness`, `dataThrough`, `calculatedAt`, projection `stale`.

Machine operational current возвращает `effectiveState`, `calculatedState`, `stateSource`, `stateSince`, optional rule/incident/reason references, evaluation quality, last telemetry time, projection currency и featured signal values. Manual state не скрывает underlying OFFLINE/data-quality fields.

## Metrics

`Metrics` возвращает additive durations в секундах (`covered`, RUN, IDLE, DOWN, SETUP, PLANNED_STOP, effective/underlying OFFLINE), output/scrap/goodOutput, event counts, optional Availability/Performance/Quality/OEE/dataCoverage/MTBF/MTTR и production unit. Percentages передаются ratio `0..1`, кроме Performance, который может превышать 1.

Line/Enterprise сначала суммируют additive facts и затем пересчитывают ratios. Несовместимые production units или отсутствующие inputs дают `null` production metrics и diagnostics, но не скрывают time metrics.

## Timeseries and losses

Resolution: `AUTO`, `5m`, `15m`, `1h`, `1d`. AUTO выбирает 5m до 12h, 15m до 2d, 1h до 14d, 1d до 90d. Subday buckets UTC-aligned; 1d использует local day Enterprise.

Loss item содержит `kind: REASON|UNCLASSIFIED|OTHER`, optional reason identity/display fields и duration. Это не JSON map: `reasonId=null` допустим и не должен смешивать UNCLASSIFIED с synthetic OTHER.

Chronometry response содержит `occurrences[]`; каждая occurrence возвращает Shift identity, `shiftDate`, UTC boundaries, totals и exact effective intervals. State interval содержит effective/calculated states, source, incident IDs, reason, quality and clipped boundaries.

## ManualIncident

Create/Update принимает `from`, nullable `to`, nullable `stateOverride`, nullable `lossReasonId`, optional comment; хотя бы один effect обязателен. Create также допускает optional untrusted `author`; update его не меняет. Response добавляет derived `effectType`, timestamps, `cancelledAt` и recalculation currency.

`stateOverride` ограничен `SETUP|PLANNED_STOP`. `to=null` означает ongoing. Future boundaries запрещены. State overlap и reason overlap проверяются независимо.

## Recalculation job

Create принимает `scope: PERIOD` с `from/to` либо `scope: ALL`. Response содержит requested/effective ranges, `PENDING|RUNNING|SUCCEEDED|FAILED`, progress `0..1`, created/started/completed timestamps и optional structured error.
