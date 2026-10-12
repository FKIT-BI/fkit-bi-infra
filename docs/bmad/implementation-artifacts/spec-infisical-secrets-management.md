---
title: 'Infisical self-hosted для управления секретами Dev и GitHub Actions'
type: 'feature'
created: '2026-10-12'
status: 'in-review'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '0cec0825790a6fbff9f02286a561db82d2a28396'
baseline_commits:
  fkit-bi-web: '8146b0df1b385a45d69b8f31fb8ddd5a43afd63f'
  fkit-bi-analytics: '3d323b770e5e110d6cbda3cf11ebba0185c41b85'
  fkit-bi-generator: 'a25cc299eaf997510d15b572f7be18ba31884ff5'
context:
  - 'fkit-bi-infra/docs/bmad/planning-artifacts/research/technical-infisical-on-develop-server-with-later-g-2026-10-12/research.md'
  - 'fkit-bi-infra/docs/ci-cd.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Секреты Dev распределены между Actions и private `.env` на VM; часть Actions-секретов нельзя прочитать обратно, а новый сервис должен иметь надёжную точку входа и восстановления.

**Approach:** Развернуть Infisical на `https://secrets.kitexp.ru`, отдельно сохранить ключ восстановления и проверить UI/canary. Перенести согласованные Actions credentials в Infisical и подключить deploy jobs через OIDC. Deploy получает актуальные значения и перезапускает нужные приложения, но не меняет пароли в базах или сервисах автоматически. Если оператор меняет пароль, он отдельно синхронизирует его с целевой системой, обновляет Infisical и запускает delivery/restart. `FKIT_BI_GITHUB_TOKEN` остаётся в GitHub для межрепозиторного checkout; встроенный `GITHUB_TOKEN` для GHCR также остаётся.

## Boundaries & Constraints

**Always:** Сохранить BI PostgreSQL data/volume. Deploy не меняет пароли целевых систем автоматически: пароль сначала вручную меняется в целевой системе, затем синхронизируется с Infisical, после чего перезапускается только зависимое приложение. Infisical PostgreSQL/Redis изолировать отдельной сетью/томами; наружу открыть только HTTPS. Отключить telemetry/announcements. Новые секреты не печатать, не коммитить и не выдавать PR-коду; OIDC ограничить конкретными repos/jobs. Не менять scope оставленного `FKIT_BI_GITHUB_TOKEN`. `ENCRYPTION_KEY` хранить отдельно от Infisical DB, в пользовательской локальной копии вне репозитория с правами `0600` и в защищённой копии на VM; не показывать значение в чате или логах. Старые Actions Secrets удалять только после cutover и health-check.

**Never:** Не удалять volumes, не публиковать DB/Redis ports, не помещать секреты в repo/logs/GitHub Variables и не выдавать их PR verify без безопасной изоляции.

## I/O & Edge-Case Matrix

| Сценарий | Вход / состояние | Ожидаемый результат | Обработка ошибки |
|----------|--------------|---------------------------|----------------|
| Запуск сервиса | DNS/TLS готовы | UI и тестовый секрет доступны по HTTPS; ключ восстановления хранится отдельно | При ошибке не переносить реальные секреты и не менять BI |
| Обновление конфигурации | Секрет обновлён и целевая система синхронизирована оператором | Deploy перечитывает значение и перезапускает нужный сервис | Не менять пароль целевой системы автоматически; при health failure не удалять старые Secrets |
| Получение по OIDC | Доверенный deploy в `develop` | Выданы только разрешённые repo/job secrets; PR не получает Infisical identity | Ошибка блокирует deploy без вывода секретов; оставленный GitHub token не меняется |

</frozen-after-approval>

## Code Map

- `compose.yaml` — BI PostgreSQL/volume, JWT, Grafana и bootstrap; Infisical нужны отдельные services/volumes/networks.
- `nginx/tls.conf.template`, `certbot/setup.sh`, `certbot/test_setup.py` — три текущих SAN/host; добавить маршрут и точный SAN `secrets.kitexp.ru`. Wildcard `*.bi.kitexp.ru` его не покрывает.
- `scripts/deploy-infra.sh`, `scripts/test-delivery.sh`, `scripts/validate.sh` — явный список сервисов, preflight и тесты; запускать Infisical без лишнего перезапуска BI.
- `docs/dev-deployment.md`, `docs/ci-cd.md` — операционные процедуры. Org Secrets: Grafana password (infra-only), Postgres password, SSH private key и GitHub token (все repos); значения не читались. Built-in `GITHUB_TOKEN` остаётся для GHCR.
- Four `.github/workflows/ci.yml` — deploy runners `ubuntu-latest`; OIDC выдавать только доверенным jobs. Infra verify сейчас использует cross-repo token для приватных checkout.
- `fkit-bi-analytics/src/main/java/ru/fkit/bi/analytics/auth/BootstrapUserCommand.java` — one-shot создание начального пользователя только при пустой таблице; повторный запуск не меняет пароль. Analytics repo также имеет несвязанный untracked `.gigaide/`, который нельзя менять.

## Tasks & Acceptance

**Выполнение:**
- [x] `fkit-bi-infra/compose.yaml` — добавить закреплённые Infisical/PostgreSQL/Redis services, volumes, isolated network и privacy opt-outs.
- [x] `fkit-bi-infra/nginx/tls.conf.template`, `fkit-bi-infra/certbot/setup.sh`, `fkit-bi-infra/certbot/test_setup.py` — добавить HTTPS host/SAN и регрессионные тесты, сохранив текущие маршруты.
- [x] `fkit-bi-infra/docs/dev-deployment.md` — описать operator bootstrap, отдельную копию `ENCRYPTION_KEY`, проверку backup/restore и вход администратора.
- [x] `fkit-bi-infra/scripts/deploy-infra.sh`, `fkit-bi-infra/scripts/test-delivery.sh` — получать секреты из Infisical для конфигурации и перезапуска без автоматической смены паролей целевых систем.
- [x] `fkit-bi-analytics/src/main/java/ru/fkit/bi/analytics/auth/BootstrapUserCommand.java` и `fkit-bi-analytics/src/test/java/ru/fkit/bi/analytics/auth/AuthFlowTest.java` — оставить bootstrap идемпотентным и без команды ротации существующего admin password.
- [x] `fkit-bi-infra/.github/workflows/ci.yml` — подключить OIDC с минимальными правами только к deploy job; оставить `FKIT_BI_GITHUB_TOKEN` для текущего verify/checkout.
- [x] `fkit-bi-web/.github/workflows/ci.yml`, `fkit-bi-analytics/.github/workflows/ci.yml`, `fkit-bi-generator/.github/workflows/ci.yml` — получать разрешённые deploy secrets по OIDC только в отдельных deploy jobs; обновить проверки и документацию.
- [ ] Удалить остальные пользовательские Actions Secrets после cutover и проверки отката.

**Критерии приёмки:**
- Дано: DNS/TLS готовы. Когда оператор открывает сервис, тогда UI работает по HTTPS, canary читается, BI health остаётся green.
- Дано: Infisical возвращает текущие runtime secrets. Когда выполняется delivery, тогда пароли целевых систем не меняются автоматически, нужные приложения перезапускаются и health проходит.
- Дано: оператор отдельно изменил секрет в целевой системе и Infisical. Когда выполняется delivery, тогда приложение получает новое значение после перезапуска.
- Дано: доверенный deploy запрашивает secrets по OIDC. Когда выдача выполняется, тогда доступны только разрешённые repo/job/path, а PR не получает Infisical identity.
- Дано: есть backup БД и отдельный `ENCRYPTION_KEY`. Когда выполняется пробное восстановление, тогда секреты расшифровываются до удаления прежних credentials.

## Implementation Notes

Локальная доставка проверена `scripts/test-delivery.sh`; прошли также проверки
runtime contracts, маршрутов Nginx, DNS hook (12 тестов) и hostname SAN
самоподписанного сертификата. Полная `scripts/validate.sh` дошла до сборки
monitoring-isolation образа, затем остановилась из-за временной DNS-ошибки Alpine
repository. `AuthFlowTest` не удалось запустить: в среде нет Java/JAVA_HOME.
Производственный cutover не запускался: DNS/TLS, OIDC identities и права project/path
требуют операторской настройки. Старые Actions Secrets не удалены до приёмки и
проверки отката. Фактическое чтение canary через UI/OIDC и пробное восстановление
БД с расшифровкой остаются production-проверками.

## Spec Change Log

- 2026-10-12: По уточнению пользователя исключена runtime-ротация. Infisical служит хранилищем/точкой получения; смена пароля целевой системы отдельна от deploy, который только применяет конфигурацию и перезапускает выбранное приложение.

## Review Triage Log

| Finding | Вердикт и evidence | Маршрут |
|---------|--------------------|---------|
| Web/Analytics/Generator держат `GH_TOKEN` на весь deploy job | medium — токен доступен Infisical action и последующим шагам, хотя нужен только при приватном clone infra | patch: ограничить clone step, отделить deploy step |
| Secrets Action указан под изменяемым tag | medium — изменение tag повлияет на job, получающий OIDC и секреты; release v1.0.9 имеет проверенный commit `8a06c1bdcd5b8635d510c52d4b57a92c1ccef785` | patch: закрепить SHA и описать процесс обновления |
| `.env` получает новый пароль PostgreSQL раньше успешного `ALTER ROLE` | false после уточнения scope — deploy не должен менять пароль роли автоматически; этот путь удаляется |
| Redis готовность проверяется только `service_started` | medium — Infisical может стартовать до готовности Redis | patch: добавить ping healthcheck и `service_healthy` |
| Нет container healthcheck для Infisical | medium — Compose может считать процесс запущенным до готовности API | patch: `/api/status`, ожидание healthy при запуске proxy |
| Не описано закрытие публичной регистрации | medium — оставшаяся открытой signup-настройка допускает незапрошенное создание учётных записей | patch: отключить и проверить signups после bootstrap |
| Нет безопасной инструкции генерации `AUTH_SECRET` | low — оператор может выбрать слабое/повторно используемое значение | patch: генерировать через CSPRNG в закрытый файл |
| Нет порога остановки по ресурсам | low — оператор может начать rollout при слишком малых ресурсах; при этом текущий read-only preflight показал 6.4 GiB свободной RAM и 41 GiB диска | patch: добавить preflight и консервативный порог demo |
| Restore описан без воспроизводимых команд | medium — acceptance restore/decrypt нельзя повторить по текущим шагам | patch: описать изолированный Compose project и проверку canary |
| Audit log acceptance не указывает поля проверки | low — оператор не сможет воспроизводимо проверить actor/path/успешный read | patch: добавить конкретные UI/log checks |
| Частичный `scp` upload оставляет ранее скопированные секреты в `/tmp` | medium — сбой следующей передачи оставит временные plaintext credentials на VM | patch: remote cleanup в local EXIT trap |
| Пароль Infisical с URI-reserved символами нарушает `DB_CONNECTION_URI` | medium — Compose напрямую интерполирует пароль в URL; документация требовала hex, но код не проверял ограничение | patch: отклонять неподдерживаемый формат до запуска |
| `healthcheck.sh` отклоняет ровно один дополнительный URL | low — guard считает два аргумента некорректными, хотя usage обещает дополнительные endpoint'ы | patch: принимать любой один или больше дополнительных URL |
| Delivery test не фиксирует фактические URL проверок | medium — mock отвечает `UP` для любого адреса, поэтому отсутствие Infisical URL не падает | patch: журналировать вызовы и проверять URL Infisical |
| Rotate command якобы не включает ротацию | неактуально после пересогласования — команда ротации исключена из требований и удаляется |
| Runtime contract test ожидает sibling checkout `fkit-bi-web`, отсутствующий в infra CI | medium — `validate.sh` падал бы до завершения на hosted runner; проверка web теперь пропускается только если checkout недоступен, локальный multi-repo checkout продолжает её выполнять | patch: поддержать `.ci` checkout и сохранить существующий scope token |
| DNS-01 challenge для SAN `secrets.kitexp.ru` записывался в `_acme-challenge.bi.kitexp.ru` | medium — certbot передаёт `CERTBOT_DOMAIN`; DNS hook теперь строит TXT имя для каждого domain и проверяется отдельным тестом | patch: использовать домен конкретного certbot challenge |
| Backup создавал timestamped dump, а restore читал несуществующий `infisical-latest.dump` | medium — backup теперь атомарно обновляет относительную ссылку `infisical-latest.dump` | patch: связать restore с созданным backup |
| Restore readiness жёстко задавал пользователя `infisical` | medium — Compose позволяет настроить `INFISICAL_POSTGRES_USER`; проверка теперь читает пользователя и БД контейнера | patch: использовать переменные Compose Postgres |
| Restore runbook не останавливал временный проект и оставлял override-файл | low — runbook теперь содержит `compose down` без volumes и удаление только временного override | patch: добавить явные команды очистки |
| Proxy ожидал `infisical: service_healthy` на старте | medium — отказ Infisical мог блокировать запуск BI proxy; DNS upstream теперь разрешается Nginx во время запроса и compose dependency удалён | patch: изолировать startup proxy от readiness Infisical |
| HTTP-01 предположительно выдавал сертификат до запуска proxy | false — `deploy-infra.sh` проверяет listener и при его отсутствии сначала поднимает proxy с `TLS_MODE=off`, затем вызывает Certbot |
| Canary audit инструкция ожидала test-workflow, но размещала canary в отдельном project | medium — OIDC role не имела доступа к нему; инструкция теперь кладёт canary в разрешённый `/github-actions/infra` и проверяет trusted deploy event | patch: согласовать canary, OIDC path и audit event |
| `.env.example` не показывал форматы Infisical bootstrap значений | low — добавлены комментарии с длинами/генерацией encryption key, auth secret и DB password | patch: описать форматы рядом с placeholders |
| Не подтверждено наличие `curl` внутри pinned Infisical образа | false — Dockerfile тега `v0.165.16` устанавливает `curl` как runtime dependency: https://github.com/Infisical/infisical/blob/v0.165.16/Dockerfile.standalone-infisical |
| Self-signed smoke test не проверял hostname нового SAN | medium — проверка `openssl x509 -checkhost secrets.kitexp.ru` добавлена до и после восстановления сертификата; проверена локально | patch: проверить SAN нового endpoint |

## Design Notes

Сначала DNS/TLS и canary, затем Actions cutover. Неизвлекаемые значения GitHub Secrets заменяются новыми только там, где это требуется интеграции; cutover не является runtime-ротацией паролей. Пользователь оставляет `FKIT_BI_GITHUB_TOKEN` в GitHub для межрепозиторного checkout; остальные согласованные Actions secrets переводятся в Infisical.

## Verification

**Команды:**
- `./scripts/validate.sh` — ожидается успешная проверка Compose/Nginx/Certbot/workflows без обращения к production DNS/ACME.
- HTTP-проверки `https://secrets.kitexp.ru/`, `https://bi.kitexp.ru/`, `https://api.bi.kitexp.ru/actuator/health`, `https://generator.bi.kitexp.ru/actuator/health` — ожидаются корректный TLS и healthy API.

**Ручные проверки:** Убедиться в корректных OIDC identity/audit logs, отсутствии доступа PR jobs, доступности UI администратору и тестового секрета, изоляции DB/Redis, наличии recovery copy и отсутствии секретов в GitHub logs, git diff и Actions summaries.
