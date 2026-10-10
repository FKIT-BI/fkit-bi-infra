# Requirement → OpenAPI operation → acceptance traceability

The API contracts collectively expose 77 operations: 63 Analytics, 12 Generator and 2 Auth. CI must compare parsed `operationId` sets to this catalog and fail if an operation is added/removed without an acceptance/test mapping. This document groups operation IDs by behavior; field and status details stay in OpenAPI.

| API contract / operation IDs | Acceptance | Test layers |
|---|---|---|
| Auth: `login`, `createUser` | AC-10, AC-11 | API contract, auth integration, end-to-end |
| Enterprise: `listEnterprises`, `createEnterprise`, `getEnterprise`, `updateEnterprise`, `updateEnterpriseStatus` | AC-1, AC-11 | API contract, PostgreSQL integration, end-to-end |
| Shifts: `listShifts`, `createShift`, `getShift`, `updateShift`, `updateShiftStatus` | AC-1, AC-7 | Unit time/DST, API contract, PostgreSQL integration |
| Loss reasons: `listLossReasons`, `createLossReason`, `getLossReason`, `updateLossReason`, `updateLossReasonStatus` | AC-6 | API contract, integration, end-to-end |
| Lines: `listLines`, `createLine`, `getLine`, `updateLine`, `updateLineStatus` | AC-1, AC-11 | API contract, PostgreSQL integration, end-to-end |
| Machines: `listEnterpriseMachines`, `createMachine`, `listLineMachines`, `getMachine`, `updateMachine`, `updateMachineStatus`, `getMachineActivationReadiness`, `assignMachinesToLine` | AC-1, AC-11 | API contract, property/integration, end-to-end |
| Components: `listMachineComponents`, `createComponent`, `getComponent`, `updateComponent`, `updateComponentParent`, `updateComponentStatus` | AC-1, AC-11 | API contract, cycle/ownership property, PostgreSQL integration |
| Signals: `listTelemetrySignals`, `createTelemetrySignal`, `getTelemetrySignal`, `updateTelemetrySignal`, `updateTelemetrySignalStatus` | AC-1, AC-2, AC-11 | API contract, integration, golden data |
| State config: `getMachineStateConfiguration`, `replaceMachineStateConfiguration`, `validateMachineStateConfiguration` | AC-2, AC-5 | Unit/property, API contract, golden data |
| Equipment and current operations: `getEquipmentTree`, `getEnterpriseOperationsOverview`, `getMachineOperationsCurrent`, `getMachineTelemetryCurrent` | AC-1, AC-2, AC-7 | API contract, PostgreSQL integration, golden/load |
| Analytics reads: `getAnalyticsSummary`, `getMetricTimeseries`, `getTelemetrySeries`, `getLossTimeseries`, `getLossPareto`, `getMachineChronometry`, `listMachineStateIntervals` | AC-3, AC-4, AC-7 | Metric unit, SQL integration, golden/load |
| Incident reads/writes: `listEnterpriseIncidents`, `listMachineIncidents`, `createManualIncident`, `getManualIncident`, `updateManualIncident`, `cancelManualIncident`, `closeManualIncident` | AC-6, AC-10 | API contract, transaction/idempotency integration, golden |
| Recalculation: `listMachineStateRecalculations`, `createStateRecalculation`, `getStateRecalculation` | AC-4, AC-5 | API contract, worker/recovery integration, golden |
| Generator scenarios: `listScenarios`, `createScenario`, `validateScenarioDraft`, `getScenario`, `updateScenario`, `updateScenarioStatus` | AC-8, AC-9 | API contract, unit validation, PostgreSQL integration |
| Generator runs: `listRuns`, `createRun`, `validateRun`, `getRun`, `stopRun`, `retryRun` | AC-8, AC-9, AC-10 | API contract, concurrency/recovery integration, golden/load |

## Cross-cutting assertions for all 77 operations

- Authenticated business operations enforce Bearer JWT; Auth bootstrap/login exceptions follow `auth-api.yaml` exactly.
- Path/query/body schemas and required fields match the OpenAPI document; timestamps use ISO-8601 offsets/UTC-compatible instants as specified.
- Success status, response schema, common error model, trace header and validation/conflict behavior are asserted.
- List/query operations test empty result, bounded pagination/range, and correct ownership scoping where applicable.
- Mutation operations test success, invalid input, missing resource, ownership mismatch, and database rollback/no partial result where applicable.
