# Доставка инфраструктуры на Dev и восстановление

Push в `develop` сначала запускает `./scripts/validate.sh`, затем — только при
`FKIT_BI_DEV_DEPLOY_ENABLED=true` — доставляет ровно `$GITHUB_SHA`. Pull request
в `develop` выполняет только проверки. Перед SSH workflow проверяет обязательные
настройки; их отсутствие завершает job до изменения сервера и без вывода значений
секретов. При выключенной доставке в GitHub summary записывается её статус.

Workflow сервисов клонируют этот репозиторий из `develop`, поэтому используют
актуальный общий delivery-скрипт. После обновления контейнера analytics и
generator проверяются через `/actuator/health` на порту 8080, а nginx-контейнер
web — запросом к `/` на порту 80. Сервисный workflow меняет ссылку образа только
для выбранного сервиса; общий серверный `flock` сериализует все доставки.

`scripts/deploy-infra.sh <sha>` использует strict host-key checking, временный
ключ с режимом `0600` и общую серверную блокировку
`/tmp/fkit-bi-deploy.lock`. Runner передаёт проверенный Git bundle, поэтому Dev
серверу не нужны GitHub credentials. Скрипт проверяет commit во временном git
worktree вместе с private `.env`, затем переводит основной checkout на detached
exact SHA; на первом запуске Git metadata создаются в существующем каталоге без
замены `.env` и Docker volume. Скрипт собирает только закреплённый Certbot helper
image, не собирает и не скачивает образы приложений, не меняет их references и не
пересоздаёт `web`. Он запускает business services, observability stack и renewal
helper; proxy пересоздаётся для применения Nginx. Nginx-конфигурация проверяется
на runner; если закреплённого `nginx:1.27-alpine` ещё нет на Dev, загружается
только этот proxy-образ. В завершение из runner проверяются
`/`, `/api/analytics/actuator/health` и `/api/generator/actuator/health`.

## Историческое подтверждение первичной готовности стенда (2026-10-04)

На 2026-10-04 Dev подтверждён снаружи: `/` и оба API health endpoint вернули
HTTP 200; backend ответил `{"status":"UP"}`. Infra `f08d8eb8004538f70e7b4c04fbfb553a0d02a287`
доставлен run [37221910438](https://github.com/FKIT-BI/fkit-bi-infra/actions/runs/37221910438).
Текущие сервисные образы опубликованы и доставлены:

- Analytics `676eeec8f3d90e8ec52bfbe62e9243c8070fd52f` — [run 37222329237](https://github.com/FKIT-BI/fkit-bi-analytics/actions/runs/37222329237).
- Generator `fb30e77daddd4bffc4e6cfed3a0e3fa84a005c82` — [run 37222336099](https://github.com/FKIT-BI/fkit-bi-generator/actions/runs/37222336099).
- Web `b7d3ac87887dc671c200a49bf5a71b29376f47d5` — [run 37221632140](https://github.com/FKIT-BI/fkit-bi-web/actions/runs/37221632140).

Обычная работа после bootstrap: отправляйте feature branch и открывайте PR в
`develop`; после merge push запускает CI, публикацию образа с тегами `dev` и
commit SHA и delivery только изменённого сервиса. Infra workflow доставляет
Compose/nginx-конфигурацию по push в `develop`.

Исторически проверенный endpoint Dev на 2026-10-04: `http://45.132.176.28:8080`.
Это прежний временный endpoint; текущий Compose публикует только порты 80/443 через
Nginx, IP остаётся доступен по HTTP на порту 80. Целевая схема сохраняет
доступ и по публичному IP, и по `bi.kitexp.ru`: домен обслуживается через Nginx на 80/443 с автоматическим
Certbot DNS-01 для `bi.kitexp.ru` и `*.bi.kitexp.ru`; IP остаётся доступен по HTTP
без требования HTTPS по IP. Создать только DNS A `bi.kitexp.ru -> 45.132.176.28`;
отдельные `api.bi.kitexp.ru`, `generator.bi.kitexp.ru` и wildcard A не нужны,
поскольку API идут по путям одного host. Certbot DNS-01 автоматически создаёт
временную TXT-запись `_acme-challenge.bi.kitexp.ru` через Yandex Cloud DNS API.
DNS не задаёт порт. На cloud firewall/security
group разрешить входящий TCP 80 и 443 на этот сервер; не открывать наружу 8080/5432.
AAAA публиковать только при рабочем IPv6.
Конфигурация сервера — `/opt/fkit-bi/.env`
(режим 600, никогда не коммитится); PostgreSQL хранится в named volume
`postgres-data`. Никогда не выполняйте `docker compose down -v`.

### Текущее состояние (2026-10-11)

Инфраструктурный CI run [38150249821](https://github.com/FKIT-BI/fkit-bi-infra/actions/runs/38150249821)
успешно выполнил `verify`, но Dev delivery остановился на удалённом preflight:
в приватном `/opt/fkit-bi/.env` остался placeholder `GRAFANA_ADMIN_PASSWORD`.
Infra SHA не применён этим run. Внешняя диагностика по старому `:8080` показала
HTTP 200 для `/`, 502 для Analytics health и timeout для Generator health; на
порту 80 корректного HTTP-ответа не было. Поэтому стенд сейчас не считается
готовым, даже если главная страница на прежнем порту отображается. Actions URL
для healthcheck уже переключён на `http://45.132.176.28`, как соответствует
публикации Nginx на порту 80. Повторить delivery после установки непустого
Grafana-пароля в приватном `.env`; значения секретов не выводить в логи.

Infra delivery получает `FKIT_BI_DEV_GRAFANA_ADMIN_PASSWORD` из Actions secret.
Если в `.env` ещё стоит известный placeholder, доставка запишет значение в файл
с режимом `0600`, сбросит пароль Grafana и удалит временную копию. Пароль не
попадает в журналы. Последующая ротация выполняется отдельно и не сбрасывается
каждой infra-доставкой.

Для первичного запуска, когда опубликованы все текущие образы, выполните на
сервере из каталога deployment:

```bash
FKIT_BI_DEV_PUBLIC_URL=http://host:port ./scripts/bootstrap-dev.sh
```

### TLS и observability

По умолчанию `TLS_MODE=off`: Nginx принимает HTTP на 80, TLS listener не создаётся,
Certbot не обращается к DNS. `TLS_MODE=self-signed` создаёт certificate/key в
persistent volume `certbot-data` в отдельном от Certbot public lineage каталоге;
они сохраняются при перезапуске и браузеры будут
показывать предупреждение о недоверенном сертификате. `TLS_MODE=public` запрашивает
SAN `bi.kitexp.ru` и `*.bi.kitexp.ru` через Certbot DNS-01 и Yandex Cloud DNS.
При обновлении старой установки unmanaged certificate из прежнего public lineage
текущие certificate и key сохраняются отдельными обычными файлами в `self-signed`
перед перемещением старого каталога с относительными Certbot-ссылками.

Для public mode задайте `CERTBOT_EMAIL`, `DNS_ZONE_ID`, `YANDEX_SERVICE_ACCOUNT_ID`,
`YANDEX_KEY_ID`, `YANDEX_SERVICE_ACCOUNT_KEY_FILE` и `DNS_RECORD_NAME` в private
`.env`. Ключ service account храните вне Git; выдайте ему только `dns.editor` для
целевой зоны. При отсутствии сертификата ошибка ACME/DNS останавливает Nginx; при
ошибке renewal предыдущий certificate остаётся на месте, сообщение пишется в лог,
следующая проверка повторяется через 12 часов. Auth/cleanup hooks используют
Yandex Cloud DNS REST API и удаляют только значение challenge, созданное текущим
запросом. `./scripts/validate.sh` запускает mock DNS tests без production
credentials, проверяет HTTP/TLS маршруты через Nginx в режимах `off`,
`self-signed` и `public`, а также кратковременно поднимает отдельный Compose smoke
stack с тестовой БД и образами приложений. Smoke test проверяет scrape targets,
datasource и шесть dashboards, затем по очереди останавливает Prometheus и Grafana
и проверяет readiness, metrics endpoint и login API. Тестовые контейнеры и volumes
удаляются после выполнения; production DNS и ACME не используются.

Ожидание DNS после создания TXT регулируется `DNS_PROPAGATION_WAIT_SECONDS`
(по умолчанию 20 секунд). Если DNS-01 выдача не проходит, проверьте TXT-запись
командой `dig TXT _acme-challenge.bi.kitexp.ru` и увеличьте ожидание в приватном
`.env` до фактической задержки propagation зоны. После выпуска проверьте, что
SAN сертификата содержит apex `bi.kitexp.ru` и wildcard `*.bi.kitexp.ru`:

```bash
echo | openssl s_client -connect bi.kitexp.ru:443 -servername bi.kitexp.ru 2>/dev/null \
  | openssl x509 -noout -ext subjectAltName
```

Периодически проверяйте, что сертификат действителен ещё как минимум 14 дней:

```bash
docker compose exec -T proxy openssl x509 \
  -in /etc/letsencrypt/live/bi.kitexp.ru/fullchain.pem \
  -checkend 1209600 -noout
```

При ненулевом коде проверьте логи renewal helper и повторите renewal до истечения
сертификата.

Задайте `FKIT_BI_DEV_GRAFANA_ADMIN_PASSWORD` как GitHub Actions secret;
bootstrap заменяет известный placeholder в private `.env` и проверяет значение
до старта Compose.
Grafana публикуется только на `127.0.0.1:${GRAFANA_PORT:-3000}`; подключайтесь через
SSH tunnel. Prometheus и exporters доступны только внутри Compose network. Compose
provisioning создаёт datasource, шесть dashboards и alert rules. Остановка
Prometheus или Grafana не является readiness-зависимостью Analytics/Generator.

Если публичный выпуск сертификата не удался, проверьте `docker compose ps` и
последние строки `docker compose logs --tail=100 cert-setup proxy`; не печатайте
`.env` или ключ service account. Исправьте DNS-записи, доступность Yandex DNS API
или параметры key/zone, затем повторите `docker compose run --rm cert-setup`.
Пересоздавайте proxy только после успешной подготовки сертификата:
`docker compose up -d --no-deps --force-recreate proxy`. Пока DNS не восстановлен,
оставляйте IP-only режим явно заданным как `TLS_MODE=off`; `TLS_MODE=public` не
переключается автоматически на другой режим.

При ошибке сохраните диагностические данные командой `docker compose ps` и
`docker compose logs --tail=100 <service>`. Восстанавливайте только известную
предыдущую ссылку образа в private `.env`, затем запускайте
`docker compose up -d --no-deps <service>`; не удаляйте volume и не раскрывайте
содержимое `.env`.
