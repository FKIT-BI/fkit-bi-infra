---
title: 'Общая OIDC identity Infisical для DEV-деплоев'
type: 'feature'
created: '2026-10-12'
status: 'in-progress'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '65b4ece3cfa8b66a039876ff8a2e3a2c106a8e97'
context:
  - 'fkit-bi-infra/docs/bmad/project-context.md'
  - 'fkit-bi-infra/docs/ci-cd.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Четыре DEV workflow уже используют Infisical OIDC, но GitHub Actions Variable с ID общей Machine Identity отсутствует; живой обмен OIDC, доступ к папкам и DEV deploy ещё не подтверждены.

**Approach:** Завершить интеграцию одной общей identity `github-infra-dev` (`6214b351-e1af-4180-9e74-e20e1073a97b`) для четырёх согласованных репозиториев. Проверить и сделать явным совпадение OIDC audience, сохранить чтение только соответствующей папки `dev`, затем провести разрешённые DEV workflow и health checks.

## Boundaries & Constraints

**Always:** Сохранять feature/PR проверки без деплоя и deploy только при `push` в `develop`; OIDC issuer `https://token.actions.githubusercontent.com`; audience `https://github.com/FKIT-BI`; claims допускают только четыре фактических репозитория и `refs/heads/develop`; `id-token: write` только в deploy job; секреты не логировать, не коммитить и не публиковать artifacts.

**Never:** Не создавать дополнительные identities; не использовать Client Secret, Universal Auth или постоянный `INFISICAL_TOKEN`; не расширять claims для прохождения проверки; не затрагивать PROD, ротацию или удаление старых GitHub secrets; не менять и не удалять посторонние незакоммиченные данные.

## I/O & Edge-Case Matrix

| Сценарий | Состояние | Ожидаемое поведение | Обработка ошибки |
|---|---|---|---|
| OIDC + чтение | Push из `develop`, корректные claims и Read grant | Загрузить секреты только из папки репозитория | Не раскрывать значения в логах |
| OIDC отклонён | Identity/audience/issuer/claims не совпали | Job завершается ошибкой до чтения | Сверить поля, не ослабляя allowlist |
| Нет права на папку | OIDC token получен, но Read grant отсутствует | Job завершается ошибкой чтения | Исправить точечный grant в `dev` |
| Неверный путь | Slug/environment/path не существует | Job сообщает ошибку загрузки | Проверить конфигурацию без смены auth |
| PR/feature | Ref не `develop` или событие PR | Нет OIDC и deploy | Сохранить текущие ограничения |

</frozen-after-approval>

## Code Map

- `fkit-bi-infra/.github/workflows/ci.yml`, `fkit-bi-analytics/.github/workflows/ci.yml`, `fkit-bi-generator/.github/workflows/ci.yml`, `fkit-bi-web/.github/workflows/ci.yml` — текущие deploy jobs; переиспользовать action SHA `Infisical/secrets-action@8a06c1bdcd5b8635d510c52d4b57a92c1ccef785`, `method: oidc`, identity/project vars, `dev` и индивидуальные secret paths. OIDC token выдается только deploy job.
- `fkit-bi-infra/scripts/test-runtime-contracts.py` — контрактная проверка путей, SHA action, permissions и develop-only gating; расширить проверкой audience/identity/path в каждом workflow.
- `fkit-bi-infra/docs/ci-cd.md` и `fkit-bi-infra/docs/bmad/implementation-artifacts/spec-infisical-secrets-management.md` — существующая схема и процесс; обновить описание общей identity без переписывания ранее принятой intent-секции замороженной спецификации.
- GitHub owner и имена проверены по remotes/API: `FKIT-BI/fkit-bi-infra`, `FKIT-BI/fkit-bi-analytics`, `FKIT-BI/fkit-bi-generator`, `FKIT-BI/fkit-bi-web`. Пути в Infisical: `/github-actions/{infra,analytics,generator,web}` соответственно.
- Actions convention уже существует: `FKIT_BI_INFISICAL_IDENTITY_ID` и `FKIT_BI_INFISICAL_PROJECT_SLUG`; project slug `fkit-bi-ti-mx`, домен `https://secrets.kitexp.ru`, environment `dev`. Переданные оператором значения claims и folder grants пока не подтверждены live-run.
- Четыре checkout сейчас на `develop`; в analytics есть не относящийся к задаче untracked `.gigaide/`. Не изменять checkout напрямую; работать через feature branches/worktrees и сохранять этот каталог.

## Tasks & Acceptance

**Execution:**
- [ ] В организации GitHub установить Actions Variable `FKIT_BI_INFISICAL_IDENTITY_ID=6214b351-e1af-4180-9e74-e20e1073a97b`, доступную ровно четырём репозиториям; оставить существующую `FKIT_BI_INFISICAL_PROJECT_SLUG=fkit-bi-ti-mx` без изменений.
- [ ] В четырёх `ci.yml` явно задать `oidc-audience: https://github.com/FKIT-BI`; сохранить `id-token: write` исключительно для deploy job, action SHA, environment, индивидуальные пути и ограничения deploy.
- [ ] Обновить `fkit-bi-infra/scripts/test-runtime-contracts.py` и `fkit-bi-infra/docs/ci-cd.md`, чтобы единая identity, audience, project/env, пути, permissions и gating были проверяемы и документированы.
- [ ] Выполнить тесты контрактов, затем провести принятые через Git Flow изменения в `develop`; проверить живые OIDC/read/deploy/health в каждом DEV workflow. Если проверка блокирована, зафиксировать точное поле/папочный grant и не менять границы доступа.

**Acceptance Criteria:**
- Given четыре Actions workflow, when runtime-contract tests выполняются, then каждый workflow закрепляет точные ID, audience, domain, project, `dev` path и только job-level OIDC permission, а PR/feature ветки не деплоят.
- Given OIDC configuration ограничена четырьмя репозиториями и `refs/heads/develop`, when каждый DEV workflow выполняется при push в `develop`, then Infisical аутентифицирует именно общий ID и отдаёт только соответствующую папку с Read доступом.
- Given secret loading завершилось, when deploy и health checks проходят, then результат подтверждён отдельно для всех четырёх сервисов без вывода значений секретов и без PROD-изменений.

## Implementation Notes

На момент планирования локальные workflows уже содержат корректные job-level permissions, action SHA, project/environment и пути. GitHub API подтвердил owner `FKIT-BI`, отсутствие identity variable и наличие project slug variable. По официальному поведению GitHub стандартная audience равна URL owner; явный override вносится для однозначной проверки. Права Infisical, OIDC claims и фактическая доступность secrets проверяются только live workflow. Старый `FKIT_BI_GITHUB_TOKEN` нужен приватным cross-repo checkout и остаётся вне области удаления.

## Verification

**Commands:**
- `python3 fkit-bi-infra/scripts/test-runtime-contracts.py` — все четыре workflow соответствуют контрактам OIDC, путей и gating.
- В каждом репозитории GitHub Actions workflow на push в `develop` — успешны Infisical fetch, deploy и штатные health checks; вывод не содержит JWT/token/secret values.

**Побочные эффекты:** изменение Actions Variable и merge в `develop` могут запускать повторный DEV deploy/restart. Эти эффекты ограничены DEV и входят в согласованный объём.
