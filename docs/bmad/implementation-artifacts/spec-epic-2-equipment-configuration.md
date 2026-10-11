---
title: 'Конфигурация оборудования Epic 2'
type: 'feature'
created: '2026-10-11'
status: 'in-review'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: 'e480aebeaf1dd7b81b7e301f8a7db61201482f6f'
context:
  - '{project-root}/fkit-bi-infra/docs/bmad/implementation-artifacts/epic-2-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** После Story 2.1 оператор всё ещё не может настроить оборудование и правила, нужные для телеметрии и генерации.

**Approach:** Закончить Epic 2 Stories 2.2–2.5 по зависимостям: Line/Machine, Component/Signal, StateConfig/readiness, затем конфигурационный интерфейс. Соблюдать существующие доменные и OpenAPI контракты.

**Boundaries & Constraints**

**Always:** Analytics владеет `equipment`/Liquibase; backend создаёт UUID, frontend задаёт коды. Сохранять собственные статусы, ownership, JWT, запрет физического удаления. Machine создаётся `DISABLED` и только раз назначается Line своего Enterprise; batch атомарен. Component tree одной Machine без циклов; Signal ссылается только на её Component, после raw-use смысл неизменяем. Одна атомарная StateConfig; `validate` не пишет. Web использует отдельные endpoints и сохраняет ввод при ошибках. Login — через Auth API; bootstrap account создаётся командой.

**Never:** Не включать Epic 3+, перенос Machine, cascade, версии, физическое удаление, scripting или giant config request.

## I/O & Edge-Case Matrix

| Сценарий | Ввод/состояние | Результат | Ошибка |
|---|---|---|---|
| Batch assignment | Есть чужая/назначенная Machine | Все или ни одно изменение | 409 с IDs |
| Component tree | Чужой parent или цикл | Сохраняется только валидная структура | 409/422 без изменения |
| Signal/StateConfig | Есть raw-use либо неверный AST/type/reference | Смысл Signal неизменяем; validate перечисляет ошибки, invalid PUT не пишет | 409/422 |
| Web setup | Истёк JWT или API conflict/validation | Повторный вход/исправление без потери ввода | Field-level error |

</frozen-after-approval>

## Code Map

- Epic boundary/AC: `fkit-bi-infra/docs/bmad/implementation-artifacts/epic-2-context.md`; `spec-mvp-acceptance-strategy/{implementation-roadmap.md,acceptance-catalog.md}`.
- Domain source: `spec-equipment-hierarchy/equipment-model.md`, `spec-equipment-core-configuration/configuration-model.md`, `spec-sql-equipment-foundation/integrity-and-indexes.md`, `spec-telemetry-signal/signal-model.md`, `spec-machine-state-rules/{configuration-model.md,condition-ast.md}`.
- Contracts/flow: `spec-analytics-api-contract/{operation-catalog.md,api-conventions.md,frontend-flow-mapping.md}`; Analytics OpenAPI `fkit-bi-analytics/docs/contracts/analytics-api-draft.yaml`; Auth `fkit-bi-infra/docs/contracts/auth-api.yaml`.
- Backend reuse: Analytics `enterprise/`, `shift/`, `api/`, `auth/`, `db/changelog/db.changelog-master.yaml`; reuse JDBC, `TransactionTemplate`, `BusinessException`, JWT and page conventions. Add releases after `003-enterprise-shifts`; do not edit applied migrations.
- Web entry: `fkit-bi-web/src/main.tsx`, `style.css`, `vite.config.ts`, `package.json` are a bare React/Vite shell. Follow `fkit-bi-web/AGENTS.md` and architecture docs; generate typed clients from OpenAPI. Add login, keep JWT in `sessionStorage`, not bootstrap provisioning.
- Story 2.1 already provides Enterprise/Shift; see its spec/task docs for Code Map, Design Notes and decisions. Start revisions: Infra `e480aebeaf1dd7b81b7e301f8a7db61201482f6f`, Analytics `9bc209f5c70df7fcffe15a021319ae133713bde4`.

## Tasks & Acceptance

**Execution:**
- [x] Analytics `releases/004-lines-machines/`, packages `line/`, `machine/`: Story 2.2 schema and CRUD/list/status/atomic assignment.
- [x] Analytics `releases/005-components-signals/`, packages `component/`, `signal/`: Story 2.3 schemas/APIs, typed parameters, tree-cycle and same-owner rules, durable first-use lock protocol.
- [x] Analytics `releases/006-state-configuration/`, package `stateconfiguration/`: Story 2.4 JSONB config, AST validator, read/replace/validate and shared activation readiness.
- [ ] Web `src/{api,auth,setup}/`, `main.tsx`, `style.css`: Story 2.5 login and responsive setup journey, generated client, selectors and recoverable loading/error states.
- [x] Update Analytics API contract/task evidence and Epic 2 backend sprint status; backend checks run after the planned Epic implementation pass.
- [ ] Web story 2.5 remains with the Web owner; do not implement UI in this backend/infra/API scope.

**Acceptance Criteria:**
- Given Enterprise/Shift, when Lines and Machines are managed, then scoped uniqueness, ordering, one-way ownership and concurrent atomic batch assignment hold.
- Given a Machine, when its tree, Signals and StateConfig are configured, then ownership/cycles/types are validated atomically and used Signal meaning cannot change.
- Given an authenticated operator, when completing Web setup, then readiness can activate the Machine and recoverable API errors preserve input.
- Given invalid config/activation, when a write occurs, then the documented error envelope leaves committed state unchanged.

## Implementation Notes

- Stories 2.2–2.4 backend implemented. Analytics OpenAPI documents the equipment, signal, state-configuration and readiness operations; migration order is 004 → 005 → 006.
- Verification after the final planned Epic pass: `./mvnw -q test` in Maven/JDK 21 Docker with PostgreSQL Testcontainers passed; Web-side checks from the existing worktree passed before this scope clarification (2 Vitest tests, typecheck, build). No deploy or push.
- User clarified that Web implementation belongs to the Web developer. Do not treat Story 2.5 as accepted here; preserve its existing working-tree changes and hand off UI follow-ups separately.

## Spec Change Log

## Review Triage Log

- `medium` — `EquipmentConfigurationApiTest` covered activation only for a ready machine, leaving the atomic not-ready rejection unpinned. Added a test expecting 422 `ACTIVATION_NOT_READY` and persisted `DISABLED`; the targeted test passed.
- `false` — Blind Hunter: state validator always returns no warnings. The state-configuration contract defines validation errors and success, but no state-validation warning conditions; the optional warnings are explicitly activation-readiness concerns and are implemented there.
- `defer` — Blind Hunter: setup UI does not reload an already-saved state configuration when a machine is reopened. This is a Web implementation issue, now outside the backend/infra/API ownership clarified by the user; hand off to Web owner.
- `defer` — Blind Hunter: setup UI does not expose edit/disable controls for existing equipment. This is a Web workflow issue, now owned by the Web developer; hand off for product/UX treatment.
- `false` — Blind Hunter: selector catalogs stop at page 0/size 50. Current Web client requests up to 200 for enterprises, lines, machines and signals; component listing is not paginated by this API.
- `false` — Blind Hunter: disabling a line can leave a machine ACTIVE. Epic 2 context explicitly requires independent statuses and no cascade; readiness and new generator starts reject disabled required parents.
- `false` — Blind Hunter: concurrent line creates could allocate the same default sort order. Equal sort orders are explicitly allowed; ordering is deterministic by sort order then stable code.
- `false` — Blind Hunter: component `unitCode: null` bypasses the numeric-only rule. Non-numeric parameters reject any supplied `unitCode` field, including explicit null, via `has("unitCode")`.
- `false` — Blind Hunter: signal list does not check machine existence. `SignalService.page` returns 404 before querying when the machine does not exist.
- `false` — Blind Hunter: arbitrary semantic/kind filters should be rejected. The API specifies filters, but does not constrain filter values; unknown values validly select no records.
- `false` — Blind Hunter: tolerance validation misses non-finite/non-positive values. Tolerance is accepted only for DOUBLE EQ/NE and those values are checked finite and positive; all other operators reject it as an unknown field.
- `false` — Edge Case Hunter: raw-use should lock `validMin/validMax`. The signal model explicitly marks these physical-validity bounds editable after raw use; only value type, sequence kind, semantic and unit are locked.
- `medium` — Verification Gap Reviewer: a negative readiness activation API test was missing. Added an assertion for 422 `ACTIVATION_NOT_READY` and confirmed status remains DISABLED; the focused test passed.

## Design Notes

Execute 2.2 → 2.3 → 2.4 → 2.5; UI validation is advisory and backend writes repeat checks transactionally. Signal configuration takes the exclusive `signal_id` advisory lock; Epic 3 first-use writer must take the shared lock before recording usage.

## Verification

After Story 2.5 only: targeted Epic 2 Java integration/API/domain tests with PostgreSQL Testcontainers; Web `npm run typecheck` and `npm run build`; `git diff --check`, migration-order and covered OpenAPI `operationId` checks. No full suite between stories.

