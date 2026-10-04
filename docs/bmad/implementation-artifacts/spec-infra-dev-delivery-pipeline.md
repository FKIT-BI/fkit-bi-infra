---
title: 'Автоматическая Dev-доставка инфраструктуры'
type: 'feature'
created: '2026-10-04'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: 'f5f0e7b6519a01233ab503f88e078cd7e239bc00'
context:
  - 'fkit-bi-infra/docs/bmad/project-context.md'
  - 'fkit-bi-infra/fkit-bi-bootstrap-prompt.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Push в `fkit-bi-infra/develop` сейчас лишь проверяет Compose и shell-скрипты. Изменения Compose, nginx и deployment-скриптов не доставляются на Dev, поэтому bootstrap не завершён и состояние стенда не привязано к проверенному SHA infra.

**Approach:** Добавить отдельную проверяемую delivery-цепочку для infra: проверить проект, безопасно применить ровно SHA из `develop` на Dev под общей блокировкой, не пересобирать и не заменять сервисные образы, сохранить `.env` и сообщить проверяемый результат.

## Boundaries & Constraints

**Always:** Использовать строгую SSH-проверку host key, временные файлы ключа с правами 600, общую серверную блокировку `/tmp/fkit-bi-deploy.lock`, SHA вместо плавающей ветки и preflight до изменений сервера. Сохранить `/opt/fkit-bi/.env`, PostgreSQL volume и сервисные SHA; не раскрывать секреты. Работать и публиковать только из `develop`.

**Never:** Не выполнять миграции вне analytics, не пересобирать и не публиковать образы приложений из infra, не применять `docker compose down -v`, не отменять активную доставку и не менять web-контейнер без утверждённого решения.

**Decision:** Infra delivery запускает proxy и текущий опубликованный `web:dev`, затем требует успешные public `/`, analytics и generator healthchecks. Любой разработчик может вносить изменения в любой компонент в рамках задачи; CI/CD и Dev-доставка web входят в этот bootstrap scope.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
| --- | --- | --- | --- |
| Delivery | Push в `develop`, все Dev settings доступны | Runner проверяет infra, сервер получает точный SHA, Compose config валиден | В summary указаны SHA и результат |
| Missing setting | Включён deploy, но отсутствует обязательный secret/variable | Сервер не изменяется | Preflight завершается ошибкой без значения секрета |
| Invalid infra | Compose config или checkout SHA не проходит | Сервисные контейнеры и `.env` не меняются | Workflow завершается ошибкой с безопасной диагностикой |
| Web готов | Текущий `web:dev` опубликован | Infra delivery запускает web и proxy, затем проверяет `/` и оба API | При ошибке healthcheck delivery завершается ошибкой без удаления данных |

</frozen-after-approval>

## Code Map

- `fkit-bi-infra/.github/workflows/ci.yml` -- текущая CI-проверка; добавить post-verify Dev delivery на push в `develop` и preflight.
- `fkit-bi-infra/scripts/deploy-service.sh` -- образец безопасного SSH, временных key/known_hosts и host-wide `flock`; не менять его контракт доставки одного сервиса.
- `fkit-bi-infra/scripts/bootstrap-dev.sh` -- текущая первичная инициализация postgres/proxy; расширить проверяемый запуск до web/proxy по утверждённому scope.
- `fkit-bi-infra/scripts/healthcheck.sh` -- внешний контракт проверки web и двух API.
- `fkit-bi-infra/compose.yaml` -- единственный runtime contract; `.env` и named volume сохраняются.
- `fkit-bi-infra/docs/dev-deployment.md` -- описать фактический путь infra delivery и recovery.
- `fkit-bi-infra/docs/bmad/project-context.md` -- завершить BOOTSTRAP-001 только по доказательствам CI и Dev.

## Tasks & Acceptance

**Execution:**

- [x] `fkit-bi-infra/scripts/deploy-infra.sh` -- реализовать SSH-доставку точного infra SHA с preflight, блокировкой, сохранением `.env` и проверкой Compose.
- [x] `fkit-bi-infra/.github/workflows/ci.yml` -- после успешного verify запускать infra delivery только для push в `develop`; для disabled deploy писать summary, для включённого — валидировать settings до сервера.
- [x] `fkit-bi-infra/scripts/validate.sh` и CI -- проверять shell, Compose и все workflow YAML/action semantics доступным pinned инструментом.
- [x] `fkit-bi-infra/scripts/bootstrap-dev.sh` и `scripts/healthcheck.sh` -- запускать текущий web/proxy и подтверждать public `/` и оба API healthchecks.
- [x] `fkit-bi-infra/docs/dev-deployment.md` и `docs/bmad/project-context.md` -- зафиксировать команды, SHA, границы ответственности и подтверждённый status bootstrap.

**Acceptance Criteria:**

- Given push в `develop` и доступные настройки Dev, when infra CI завершается, then сервер использует тот же infra SHA, `.env` остаётся private и сервисные image references не изменяются.
- Given отсутствует обязательная настройка, when delivery включена, then workflow завершается до SSH и не меняет сервер.
- Given PR в `develop`, when CI выполняется, then проходят только проверки без доставки.
- Given error Compose или SSH, when infra delivery не может подтвердить состояние, then workflow fails without volume deletion or secret output.
- Given published `web:dev` and healthy backend containers, when infra delivery completes, then web и proxy are running and the public URL, `/api/analytics/actuator/health` and `/api/generator/actuator/health` return success.

## Implementation Notes

- 2026-10-04: analytics SHA `181220860bd282368f2bab80f214d5adf8276fd3` и generator SHA `7806f46c2c69c10158bd947409d7c08052e03c16` успешно доставлены и healthy на Dev. Web image опубликован; его delivery входит в текущий scope.

## Spec Change Log

## Review Triage Log

| Finding | Verdict | Evidence |
| --- | --- | --- |
| Blind: quoting of deploy path | medium | Подтверждено: абсолютный путь мог содержать одинарную кавычку в remote command. Исправлено allowlist-проверкой пути и покрыто тестом. |
| Blind: unbounded curl | medium | Подтверждено: `curl` мог зависнуть до перехода к retry. Исправлено `--connect-timeout` и `--max-time`; retry и exhaustion проверены. |
| Blind: unbounded SSH | medium | Подтверждено: black-hole SSH не имел собственного лимита. Добавлены `ConnectTimeout`, одна попытка и keepalive. |
| Blind: nginx до live checkout | medium | Подтверждено: Compose не читает nginx-конфигурацию. Временный worktree теперь проходит `nginx -t` с pinned образом без pull до checkout. |
| Blind: rollback после внешнего healthcheck | low | Факт смены checkout до внешнего healthcheck верен, но frozen acceptance требует fail без удаления данных/секретов, а не rollback; атомарная стратегия требует нового решения о восстановлении контейнеров и web, поэтому не добавлена. |
| Blind: отсутствие remote contract test | medium | Подтверждено. Добавлен stubbed SSH-path test: exact SHA, `.env`, nginx preflight, no-pull и `--no-recreate web`. |
| Edge: stalled endpoint | medium | Дубликат bounded-curl finding; исправление и тест указаны выше. |
| Edge: quoted deploy path | medium | Дубликат path-injection finding; исправление и тест указаны выше. |
| Edge: proxy image pull in bootstrap | false | Bootstrap намеренно не обязан обновлять proxy: infra delivery запрещено pull сервисных образов, а proxy использует pinned runtime image; утверждение о «published current proxy» не следует из runtime contract. |
| Verification: remote path coverage | medium | Подтверждено и исправлено успешным полностью stubbed SSH-path test. |
| Verification: bootstrap coverage | medium | Подтверждено и исправлено stubbed bootstrap test, который проверяет запуск всех пяти сервисов. |
| Verification: health retry coverage | medium | Подтверждено и исправлено детерминированными тестами transient success и 24 неудачных попыток. |

## Design Notes

Точный commit checkout на Dev делает результат воспроизводимым. Единый host-level `flock` остаётся общей границей сериализации для infra и сервисных доставок; GitHub concurrency этого не заменяет.

## Verification

**Commands:**

- `./scripts/validate.sh` -- expected: Compose, shell и workflow validation проходят.
- `gh run view <run> --repo FKIT-BI/fkit-bi-infra` -- expected: preflight, delivery SHA и итог без раскрытия секретов.
- `ssh … 'cd /opt/fkit-bi && docker compose config --quiet && docker compose ps'` -- expected: конфигурация валидна, `.env` сохранён, состояния сервисов видимы.
