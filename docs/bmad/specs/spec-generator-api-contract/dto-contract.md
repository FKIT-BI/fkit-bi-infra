# DTO contract

## Scenario

`ScenarioCreate` и `ScenarioUpdate` содержат identity/display fields, `cycleMode`, machine targets и phases. Create не принимает `status`; новый resource всегда `DISABLED`. Response добавляет UUID, status, timestamps и полный `ScenarioValidationResult`.

Machine target содержит `machineId` и optional `baseBehaviors`. Phase содержит stable local `code`, name, positive `durationMs`, optional diagnostic `expectedState` и compact overrides.

Behavior override — discriminated union:

- `REPLACE`: `signalId`, action и полная `behavior`;
- `DISABLE`: `signalId`, action без behavior.

Signal behavior — discriminated union по `model`. Каждый subtype задаёт только совместимые параметры и общие interval/quality/noise/missing/seed fields.

## Validation

`ValidationIssue` содержит severity, stable code, JSON path, human message и optional entity reference. `ScenarioValidationResult` возвращает `valid`, issues и counts. Warnings не блокируют activation/run; errors блокируют.

## Run create

`RunCreate` — oneOf с discriminator `mode`:

- `RealtimeRunCreate`: optional positive `durationMs`;
- `HistoricalRunCreate`: required `from`, `to`;
- `ScheduledRunCreate`: required future `scheduledStartAt` и не более одной optional границы `durationMs|eventTo`.

Каждый вариант содержит `scenarioId` и optional `randomSeed`. Нормативная validation дополнительно проверяет Scenario status, equipment readiness, concurrency, coverage и temporal semantics.

## Run response

Summary предназначен для journal; detail добавляет Scenario snapshot summary, phase/cycle, progress, counters, checkpoint, failure и `AnalyticsContext`. `progressPercent` nullable для unbounded run. `COMPLETED` не означает analytics readiness.

`RunValidationResult` содержит normalized mode/range, nullable estimates, conflicting machine/range details и issues. Estimate ориентировочный и не является SLO.
