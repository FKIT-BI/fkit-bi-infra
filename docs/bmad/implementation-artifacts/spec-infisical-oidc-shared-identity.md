---
title: 'Общая OIDC identity Infisical для DEV-деплоев'
type: 'feature'
created: '2026-10-12'
status: 'in-review'
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

**Approach:** Завершить интеграцию одной общей identity `github-infra-dev` (`6214b351-e1af-4180-9e74-e20e1073a97b`) для DEV workflows четырёх сервисных репозиториев. По явному решению владельца identity claims допускают все репозитории `FKIT-BI` на `develop`; фактическое чтение секретов ограничено отдельными Read grants к четырём папкам `dev`.

## Boundaries & Constraints

**Always:** Сохранять feature/PR проверки без деплоя и deploy только при `push` в `develop`; OIDC issuer `https://token.actions.githubusercontent.com`; workflow audience `https://github.com/FKIT-BI`; identity claims `repository=FKIT-BI/*` и `ref=refs/heads/develop`; `id-token: write` только в deploy job; секреты не логировать, не коммитить и не публиковать artifacts. Широкий org-wide claim утверждён владельцем и сохраняется.

**Never:** Не создавать дополнительные identities; не использовать Client Secret, Universal Auth или постоянный `INFISICAL_TOKEN`; не расширять grants чтения за пределы согласованных четырёх папок; не затрагивать PROD, ротацию или удаление старых GitHub secrets; не менять и не удалять посторонние незакоммиченные данные.

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
- Actions convention: `FKIT_BI_INFISICAL_IDENTITY_ID` и `FKIT_BI_INFISICAL_PROJECT_SLUG`; project slug `fkit-bi-ti-mx`, домен `https://secrets.kitexp.ru`, environment `dev`. GitHub API подтвердил ID и видимость variable для четырёх delivery repos. Claims `FKIT-BI/*` + `refs/heads/develop`, audience workflow и folder access подтверждены live-run Analytics, Generator и Web; infra delivery проверяется отдельно.
- Четыре checkout сейчас на `develop`; в analytics есть не относящийся к задаче untracked `.gigaide/`. Не изменять checkout напрямую; работать через feature branches/worktrees и сохранять этот каталог.

## Tasks & Acceptance

**Execution:**
- [x] Установить Actions Variable `FKIT_BI_INFISICAL_IDENTITY_ID=6214b351-e1af-4180-9e74-e20e1073a97b` только для четырёх репозиториев; оставить `FKIT_BI_INFISICAL_PROJECT_SLUG=fkit-bi-ti-mx` без изменений. GitHub API подтвердил visibility `selected` и ровно четыре требуемых repository IDs.
- [x] В четырёх `ci.yml` явно задать `oidc-audience: https://github.com/FKIT-BI`; сохранить `id-token: write` исключительно для deploy job, action SHA, environment, индивидуальные пути и ограничения deploy.
- [x] Обновить `fkit-bi-infra/scripts/test-runtime-contracts.py` и `fkit-bi-infra/docs/ci-cd.md`, чтобы единая identity, audience, project/env, пути, permissions и gating были проверяемы и документированы.
- [ ] Провести изменения в `develop`; проверить живые OIDC/read/deploy/health в каждом DEV workflow. Локальный контрактный тест выполнен; push/remote операции разрешены владельцем в текущем запросе.

**Acceptance Criteria:**
- Given четыре Actions workflow, when runtime-contract tests выполняются, then каждый workflow закрепляет точные ID, audience, domain, project, `dev` path и только job-level OIDC permission, а PR/feature ветки не деплоят.
- Given OIDC configuration разрешает `FKIT-BI/*` и `refs/heads/develop`, when каждый из четырёх delivery workflows выполняется при push в `develop`, then Infisical аутентифицирует общий ID и отдаёт только папку, указанную данным workflow и разрешённую его Read grant.
- Given secret loading завершилось, when deploy и health checks проходят, then результат подтверждён отдельно для всех четырёх сервисов без вывода значений секретов и без PROD-изменений.

## Implementation Notes

Первый Analytics run (`38222779544`, attempt 1, 08:18 UTC) завершил verify и publish, но OIDC был отклонён. Сравнение первоначально переданного фильтра `ORG/{fkit.bi-*}` с фактическими GitHub claims показало несовпадение owner/repository. Владелец обновил Claims на `FKIT-BI/*` и `refs/heads/develop`. Свежий диагностический run `38225351269` (attempt 1, 08:43 UTC) показал фактические `iss`, `aud`, `sub`, `repository`, `repository_owner`, `ref`, `event_name`, `workflow_ref` и `job_workflow_ref`; Infisical принял OIDC, загрузил секреты из `/github-actions/analytics`, затем DEV deploy завершился успешно. Пустой Audiences не мешает этому установленному экземпляру принимать workflow audience `https://github.com/FKIT-BI`. Analytics, Generator (`38225929029`) и Web (`38225930228`) уже прошли OIDC/read/deploy; infra ожидается. Секретные значения и JWT не выводились. Старый `FKIT_BI_GITHUB_TOKEN` нужен приватным cross-repo checkout и остаётся вне области удаления.

Реализация подготовлена на локальных feature branches в worktrees; исходные checkout и `.gigaide/` сохранены. Текущий этап не разрешает push или удалённые операции, поэтому GitHub variable, PR/merge, OIDC grant и live DEV проверки остаются невыполненными.

## Verification

**Commands:**
- `python3 fkit-bi-infra/scripts/test-runtime-contracts.py` — все четыре workflow соответствуют контрактам OIDC, путей и gating.
- В каждом репозитории GitHub Actions workflow на push в `develop` — успешны Infisical fetch, deploy и штатные health checks; вывод не содержит JWT/token/secret values.

**Побочные эффекты:** изменение Actions Variable и merge в `develop` могут запускать повторный DEV deploy/restart. Эти эффекты ограничены DEV и входят в согласованный объём.

## Review Triage Log

- medium — `scripts/test-runtime-contracts.py` мог молча пропустить обязательный checkout и проверить только infra; fixed: в infra CI обязательны analytics/generator, для полного локального/override теста обязательны все четыре. Свидетельство: тест теперь падает при отсутствии обязательного checkout.
- medium — отдельный finding о пропуске checkout указывал, что проверка могла не заметить неожиданно перемещённый checkout; fixed тем же явным списком обязательных путей и проверкой их наличия.
- medium — blind review отметил, что сообщение об успехе могло относиться к неполному набору checkout; fixed: локальный/override режим требует четыре репозитория, а CI режим явно определяет и сообщает проверяемый набор.
- medium — verification-gap review подтвердил, что пропуск analytics/generator в infra CI лишал проверку их OIDC-контрактов; fixed: эти два checkout теперь обязательны в CI.
- medium — тест deploy gate искал только подстроки event/ref, позволяя незаметно расширить условие; fixed: сравнивается полное ожидаемое выражение каждого deploy job.
- medium — broad org-wide claim позволяет любому workflow организации на `develop` аутентифицироваться, если у него есть Identity ID и `id-token: write`; владелец явно принял и подтвердил этот scope. В четырёх известных deploy workflows permission и delivery gate остаются job-level и push/develop-only; secret reads дополнительно ограничены четырьмя folder grants.
- medium — проверка отсутствия SSH key secret смотрела только на `env`; fixed: ссылка ищется во всех полях каждого deploy step.
