---
title: 'Опубликовать delivery-контур и подготовить Dev-стенд'
type: 'feature'
created: '2026-10-04'
status: 'in-progress'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: 'de21b806e39f34bbbfc0527ebb054cc563c3243a'
context:
  - 'fkit-bi-infra/docs/bmad/project-context.md'
  - 'fkit-bi-infra/docs/dev-deployment.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Delivery-пайплайны сервисов уже публикуют образы и два backend-сервиса были доставлены, но инфраструктурная доставка пока существует только в локальном commit и не запускается GitHub. Web не был доставлен, а общий service-deploy healthcheck обращается к backend-адресу, которого в nginx-контейнере web нет. В результате стенд нельзя считать воспроизводимо готовым для последующих feature-push.

**Approach:** Опубликовать текущий проверенный infra commit, скорректировать service delivery так, чтобы healthcheck соответствовал типу сервиса, и привести документацию/игнорирование generated-файлов в соответствие. Проверить CI, дождаться автоматической доставки exact infra SHA и подтвердить публичный web и оба API на Dev.

## Boundaries & Constraints

**Always:** Работать из `develop`; использовать immutable SHA-теги для сервисов; сохранять private `.env`, PostgreSQL volume и имеющиеся данные; выполнять SSH только с проверкой host key и общей блокировкой; скрывать секретные значения; проверять доставку через публичный `/` и оба API health endpoint. Analytics остаётся единственным владельцем Flyway-миграций.

**Never:** Не удалять volume, не выполнять `docker compose down -v`, не создавать новые credentials, не раскрывать значения secrets, не заменять образ другого сервиса при delivery, не публиковать или менять production-контур.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
| --- | --- | --- | --- |
| Infra release | Локальный `develop` содержит проверенный infra commit | Commit отправлен в `origin/develop`, GitHub запускает verify и enabled Dev delivery exact SHA | При ошибке workflow фиксируется URL/run и сервер не меняется до preflight |
| Backend release | Push analytics/generator в `develop` | Публикуется `:dev` и `:SHA`; обновляется только выбранный сервис, после его healthcheck | Host-level lock сериализует параллельные delivery |
| Web release | Push web в `develop` | Публикуется образ, обновляется только web и проверяется HTTP `/` на порту 80 | Неверный endpoint не маскируется успешным deploy |
| Public readiness | Образы и infra delivery завершились | `/`, `/api/analytics/actuator/health`, `/api/generator/actuator/health` возвращают success | При timeout/failure workflow завершается с безопасной диагностикой без удаления данных |

</frozen-after-approval>

## Code Map

- `fkit-bi-infra/.github/workflows/ci.yml` -- локальный commit `de21b80` добавляет post-verify Dev delivery на push в `develop`; после push это единственный путь доставки exact infra SHA.
- `fkit-bi-infra/scripts/deploy-infra.sh` -- безопасно применяет infra SHA на сервере, не меняя image references; его public healthcheck является доказательством готовности стенда.
- `fkit-bi-infra/scripts/deploy-service.sh` -- общий сервисный SSH delivery; сейчас проверяет fixed backend endpoint, поэтому требует выбора healthcheck по `analytics|generator|web`.
- `fkit-bi-infra/compose.yaml` -- web использует nginx на 80, analytics и generator слушают 8080; сохраняет runtime-contract и private `.env`.
- `fkit-bi-web/Dockerfile` -- подтверждает HTTP healthcheck web на `http://localhost/`, а не actuator.
- `fkit-bi-{analytics,generator,web}/.github/workflows/ci.yml` -- единый путь verify → GHCR (`:dev`, `:SHA`) → условный deploy для push в `develop`; общий infra deploy-скрипт нужно получать из `develop`, поскольку service delivery меняется вместе с ним.
- `fkit-bi-web/.gitignore` -- должен исключать `*.tsbuildinfo`, чтобы generated TypeScript metadata не блокировала следующие commits.
- `fkit-bi-infra/scripts/test-delivery.sh` -- contract tests infra delivery; дополнить проверками endpoint-выбора service delivery.
- `fkit-bi-infra/docs/dev-deployment.md` и `docs/bmad/project-context.md` -- операторский контракт и итоговый статус BOOTSTRAP-001 после evidence от GitHub и Dev.

## Tasks & Acceptance

**Execution:**

- [x] `fkit-bi-infra/scripts/deploy-service.sh` -- выбирать internal health URL по сервису (`/actuator/health` для backend, `/` для web) и сохранить current SSH/lock/single-service semantics.
- [x] `fkit-bi-infra/scripts/test-delivery.sh` -- покрыть service delivery endpoint и отказ до изменения сервера при неверном service input.
- [x] `fkit-bi-web/.gitignore` -- добавить generated TypeScript build info; не добавлять artifact в Git.
- [ ] `fkit-bi-infra/docs/dev-deployment.md` и `docs/bmad/project-context.md` -- зафиксировать фактическую последовательность delivery, SHAs/runs и подтверждённую либо неподтверждённую readiness.
- [ ] все изменённые Git-репозитории -- выполнить пропорциональные проверки, создать осмысленные commits и push `develop`; дождаться соответствующих Actions.

**Acceptance Criteria:**

- Given push infra SHA в `develop`, when Infra CI проходит, then GitHub доставляет тот же SHA на Dev и public web плюс оба API healthcheck успешны.
- Given web service delivery, when контейнер обновляется, then pipeline ждёт `http://localhost/`, а не backend actuator endpoint.
- Given generated `*.tsbuildinfo`, when разработчик запускает TypeScript build, then файл не становится незакоммиченным препятствием для feature push.
- Given последующий push любой feature в `develop`, when его CI succeeds, then соответствующий immutable image публикуется и только его сервис может быть доставлен без ручного редактирования server `.env`.

## Implementation Notes

- Обновлён `deploy-service.sh`: web получает healthcheck по HTTP `/`, backend — actuator; общий lock и single-service deployment сохранены.
- Добавлены stubbed delivery checks для всех трёх сервисов и отказа на неизвестном имени. `./scripts/validate.sh` и actionlint четырёх workflow прошли; web typecheck и production build прошли.
- Три сервисных workflow теперь явно клонируют infra `develop`, а web игнорирует `*.tsbuildinfo`. Публикация и фактические Dev checks ещё ожидают push.
- Push `4130bac9b4f86809e34b587071f52d1ee2189eb2`: infra verify прошёл; Dev deploy завершился на удалённом preflight без диагностического сообщения. Безопасная диагностика подтвердила, что `/opt/fkit-bi` не был Git checkout.
- Infra delivery теперь передаёт runner-собранный Git bundle и инициализирует metadata рядом с существующим `.env`, не требуя GitHub credentials на сервере. `deliver-dev` получает полную историю `develop` для проверки SHA; локальные stubbed checks прошли.
- Web commit `b7d3ac87887dc671c200a49bf5a71b29376f47d5` прошёл verify, GHCR publish и Dev service deployment в run `37221632140`.
- Infra run `37221722491` подтвердил, что у Dev отсутствует локальный `nginx:1.27-alpine`. `nginx -t` перенесён в runner preflight; сервер загрузит только фиксированный proxy-образ при его отсутствии, сохраняя образы приложений без изменений.

## Spec Change Log

## Review Triage Log

## Design Notes

Service-level healthcheck остаётся локальным после restart, поскольку именно он подтверждает новое приложение. Infra-level delivery дополняет его внешними public checks и не изменяет image references: тем самым сервисный и инфраструктурный контуры не конкурируют за одну ответственность.

## Verification

**Commands:**

- `fkit-bi-infra/scripts/validate.sh` -- expected: Compose, contract tests, shellcheck и actionlint проходят.
- `./mvnw -B verify` в analytics и generator; `npm ci && npm run typecheck && npm run build` в web -- expected: сервисные CI-команды локально проходят.
- `gh run watch <id> --repo FKIT-BI/fkit-bi-infra --exit-status` -- expected: verify и Deliver infra to Dev успешны.
- `curl --fail --silent --show-error http://45.132.176.28:8080/` и оба API health URL -- expected: public endpoints возвращают success.
