---
id: SPEC-generator-api-contract
companions:
  - operation-catalog.md
  - api-conventions.md
  - dto-contract.md
  - frontend-flows.md
  - contract-examples.md
sources: []
---

> **Canonical contract.** Этот SPEC и файлы из `companions:` составляют полный контракт Generator HTTP API и пользовательских потоков frontend.

# Generator API contract

## Why

Frontend должен настраивать и запускать воспроизводимую генерацию по существующему оборудованию, не зная JDBC writer, checkpoints и runtime workers. Отдельный компактный OpenAPI должен дать frontend и generator backend одну типизированную границу, не дублируя Analytics API и не смешивая control plane с raw ingestion.

## Capabilities

- **CAP-1**
  - **intent:** Frontend может создавать, изменять, проверять и активировать durable Scenario.
  - **success:** Шесть Scenario operations покрывают list/create/draft validation/get/full replace/status без физического DELETE.

- **CAP-2**
  - **intent:** Frontend может компактно конфигурировать много машин и фаз без повторения обычного поведения.
  - **success:** DTO использует `baseBehaviors` и одноуровневые `REPLACE|DISABLE` overrides, которые однозначно компилируются в полный Run snapshot.

- **CAP-3**
  - **intent:** Frontend может проверить, оценить и создать типобезопасный realtime, historical или scheduled Run.
  - **success:** Discriminated RunCreate variants, optional validation/estimate и required `Idempotency-Key` предотвращают условно-null DTO и duplicate starts.

- **CAP-4**
  - **intent:** Frontend может просматривать журнал, отслеживать progress, останавливать и повторять Run.
  - **success:** Шесть Run operations возвращают cursor journal, detail, idempotent stop и guarded retry с согласованными lifecycle fields.

- **CAP-5**
  - **intent:** Generator UI может загрузить рабочий контекст без чрезмерного агрегирующего ответа.
  - **success:** Equipment tree, Scenario page и Run journal загружаются тремя параллельными bounded requests, а Signals — лениво только для выбранных Machines.

- **CAP-6**
  - **intent:** Frontend может обрабатывать validation и business conflicts без разбора текста.
  - **success:** Общий `ErrorResponse`, field paths, `traceId` и стабильные 400/404/409/422/500 codes согласованы с Analytics API.

- **CAP-7**
  - **intent:** Backend и frontend могут генерировать transport boundary из одного контракта.
  - **success:** OpenAPI 3.1 проходит lint, разделяет request/response DTO и однозначно задаёт UUID, timestamps, nullability, polymorphism и examples.

## Constraints

- Нормативные operations находятся в `operation-catalog.md`, API rules — в `api-conventions.md`, DTO — в `dto-contract.md`.
- Frontend flows и допустимое число requests определены в `frontend-flows.md`; основные payload examples — в `contract-examples.md`.
- Base path внутри generator service — `/api/v1`; внешний `/api/generator/` является reverse-proxy prefix, а не частью controller paths.
- Public HTTP не передаёт raw measurements и не предоставляет equipment CRUD.
- Нормативный OpenAPI 3.1 находится в `fkit-bi-generator/docs/contracts/generator-api-draft.yaml`.
- Run creation асинхронно возвращает `202`; completion не ждёт Analytics.
- Публичные операции требуют JWT Bearer по общей границе доверия с Analytics; роли/RBAC не входят в MVP.

## Non-goals

- REST ingestion отдельных measurements или batches.
- Дублирование Enterprise/Line/Machine/Component/Signal API.
- SSE, WebSocket и push progress.
- Physical DELETE Scenario/Run.
- Recurring schedule resources.
- Управление Analytics recalculation из Generator API.

## Success signal

Сгенерированные клиенты проходят contract tests: пользователь сохраняет и активирует Scenario, проверяет и создаёт каждый тип Run, наблюдает progress, выполняет stop/retry и переходит по analytics context, не создавая duplicate Runs и не обращаясь к внутреннему telemetry writer.
