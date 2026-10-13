# FKIT BI infrastructure

Infrastructure repository for PostgreSQL, analytics, generator, web and nginx. Analytics owns the shared database migrations.

Copy `.env.example` to `.env` only on the Dev host. Run `./scripts/validate.sh` to validate Compose and scripts. Read `docs/architecture/`, `docs/development.md`, `docs/dev-deployment.md` and `docs/bmad/project-context.md` before changing shared contracts.

Создайте `FKIT_JWT_SECRET` минимум из 32 криптографически случайных байт, закодируйте Base64 и передайте его обоим сервисам через deployment environment.

Инструкции ниже описывают процедуру onboarding; сами по себе они не создают секреты и не выполняют provisioning. До передачи credentials frontend-команде оператор должен отдельно завершить и проверить шаги на Dev-стенде.

Для одноразового bootstrap-пользователя храните в пользовательском проекте Infisical, в среде `dev` и папке `/github-actions`, три секрета: `FKIT_BOOTSTRAP_USERNAME=demo.admin`, `FKIT_BOOTSTRAP_DISPLAY_NAME=Демо-администратор` и уникальный случайный `FKIT_BOOTSTRAP_PASSWORD` из 32 ASCII-символов. Сгенерируйте пароль CSPRNG-генератором менеджера паролей, не сохраняя отдельную запись; 32 равномерно выбранных символа из набора 64 дают 192 бита энтропии и укладываются в лимит 72 байта BCrypt. Введите значение напрямую в Infisical; не копируйте его в Git, файлы, аргументы shell, историю команд или вывод терминала. После авторизации Infisical CLI и выбора собственного project ID выполните на Dev-хосте:

```bash
INFISICAL_DOMAIN=https://secrets.kitexp.ru infisical run --projectId='<project-id>' --env=dev --path=/github-actions -- ./scripts/bootstrap-user.sh
```

CLI передаёт секреты только дочернему процессу; Compose передаёт три bootstrap-переменные только одноразовому сервису `analytics-bootstrap`. Команда создаёт bootstrap-пользователя только при пустой `identity.users`; повторный запуск на непустом хранилище завершится без изменения учётных записей. Пароль не выводится.

Если bootstrap-пользователь уже существует, но вход не проходит, установите в том же проекте и пути новое значение только для `FKIT_BOOTSTRAP_PASSWORD` и выполните явную одноразовую команду:

```bash
INFISICAL_DOMAIN=https://secrets.kitexp.ru infisical run --projectId='<project-id>' --env=dev --path=/github-actions -- ./scripts/reset-bootstrap-password.sh
```

Reset обновляет только BCrypt-хэш существующей bootstrap-учётки с именем `FKIT_BOOTSTRAP_USERNAME`. Он откажет, если такой bootstrap-учётки нет или имя принадлежит обычному пользователю; новую запись не создаёт. Команды не передают эти переменные в долгоживущие Analytics/Generator контейнеры.

Значение `FKIT_BOOTSTRAP_PASSWORD` в Infisical всегда должно совпадать с текущим паролем bootstrap-пользователя. При ротации обновите секрет в том же Infisical-проекте и пути и сразу выполните reset-команду выше; до успешной проверки не используйте старое и новое значения как взаимозаменяемые.

После provisioning откройте публичный Analytics Swagger по HTTPS: `https://api.bi.kitexp.ru/swagger-ui/index.html`. Этот домен ведёт на тестовый Dev-хост `45.132.176.28`; не отправляйте bootstrap credentials на HTTP/IP URL. Выполните `POST /api/v1/auth/login` с bootstrap-логином и паролем. Скопируйте `accessToken` из ответа, нажмите `Authorize` и задайте Bearer token. Токен действует 1800 секунд; если срок истёк до следующего запроса, войдите снова и авторизуйте Swagger новым токеном. Затем выполните существующий `POST /api/v1/auth/users` с полным телом, например:

```json
{
  "username": "demo.operator",
  "displayName": "Демо-оператор",
  "initialPassword": "REPLACE_WITH_A_UNIQUE_PASSWORD"
}
```

`REPLACE_WITH_A_UNIQUE_PASSWORD` — явный placeholder: замените его на отдельный случайный пароль перед запросом. Ожидаемый результат — `201` и объект с `id`, `username`, `displayName`, `createdAt`; пароля в ответе нет. Login доступен без JWT; endpoint создания пользователей требует bootstrap JWT. Прочие бизнес-операции Analytics и Generator также требуют JWT. Swagger Generator доступен без авторизации по HTTPS: `https://generator.bi.kitexp.ru/swagger-ui/index.html`.

Передайте созданному обычному пользователю его `initialPassword` только через одобренный организацией защищённый канал, отдельно от username, и не включайте пароль в тикет, чат без защиты, email без согласованной защиты или shell-команду. Проверьте учётные данные пользователя через `POST /api/v1/auth/login` по HTTPS: ожидаются `200` и безопасный ответ пользователя с `canCreateUsers: false`. Затем передайте только username и результат готовности frontend-команде. Не меняйте Infisical bootstrap-секрет на пароль обычного пользователя; bootstrap учётка остаётся операторской и её актуальный пароль хранится в Infisical.

The bootstrap credentials are passed only to the one-shot `analytics-bootstrap` container. The default Compose network uses `172.29.0.0/24`, with Nginx fixed at `172.29.0.250`; this lets Analytics trust only Nginx's overwritten client-IP header. If that subnet conflicts with the host, choose a free `COMPOSE_SUBNET`, set `PROXY_CONTAINER_IP` to an unused address inside it, and set `FKIT_TRUSTED_PROXY_CIDRS` to that Nginx address with `/32`.

TLS выбирается явно через `TLS_MODE=off` (по умолчанию), `self-signed` или
`public`. В public-режиме `CERTBOT_CHALLENGE=http-01` выпускает один сертификат
с точными SAN `bi.kitexp.ru`, `api.bi.kitexp.ru` и
`generator.bi.kitexp.ru` через общий persistent webroot. Режим
`CERTBOT_CHALLENGE=dns-01` сохраняет прежний apex+wildcard контракт и требует
внешние Yandex Cloud DNS credentials. Оба режима требуют `CERTBOT_EMAIL`.

`bi.kitexp.ru` обслуживает Web и совместимые path-based API;
`api.bi.kitexp.ru` и `generator.bi.kitexp.ru` проксируют исходный URI напрямую в
соответствующий backend. Доменные HTTP-запросы при включённом TLS перенаправляются
на HTTPS, кроме `/.well-known/acme-challenge/`; IP остаётся доступен по HTTP.
Ошибка первого public-выпуска оставляет подготовленный HTTP-контур и завершает
delivery ошибкой — self-signed fallback отсутствует. Grafana привязана только к
loopback и требует непустой `GRAFANA_ADMIN_PASSWORD`; Prometheus и exporters
остаются внутри Compose network. Операторские шаги описаны в
`docs/dev-deployment.md`.
