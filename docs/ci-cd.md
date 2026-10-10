# Памятка: CI/CD FKIT BI

## Репозитории

- `fkit-bi-web` — веб-клиент.
- `fkit-bi-analytics` — API аналитики.
- `fkit-bi-generator` — API генерации сценариев и телеметрии.
- `fkit-bi-infra` — Docker Compose, Nginx и общие скрипты доставки.

## Обычный путь изменения приложения

1. Создайте feature-ветку и откройте PR в `develop` нужного репозитория.
2. Для PR GitHub Actions выполняет проверки, но не публикует образ и не
   деплоит Dev:
   - Web: `npm ci`, typecheck, production build и Docker build.
   - Analytics и Generator: `./mvnw -B verify` и Docker build.
3. После успешных проверок смержите PR. Push результата merge в `develop`
   повторно запускает CI и затем публикует контейнер в GHCR с тегами `dev` и
   полным Git SHA коммита.
4. Если Dev-доставка включена, тот же workflow передаёт общий скрипт из
   `fkit-bi-infra/develop` и обновляет только изменённый сервис. Скрипт
   использует образ по SHA, сериализует доставки общей блокировкой и проверяет
   health endpoint.

Прямой push в `develop` тоже запускает workflow. Для обычной разработки
используйте PR, чтобы проверки прошли до попадания изменений в интеграционную
ветку. Сервисные workflow также имеют `workflow_dispatch`, но публикация и
деплой в них настроены только для события `push`.

## Что делает infra workflow

В `fkit-bi-infra` PR в `develop` запускает `./scripts/validate.sh`. Push в
`develop` сначала выполняет ту же проверку, а затем, если доставка включена,
применяет точную infra-ревизию на Dev. Workflow передаёт Git bundle, сервер
делает checkout точного SHA, проверяет Compose и применяет конфигурацию.
Infra-доставка не обновляет образы приложений; она может скачать только
закреплённый образ Nginx `nginx:1.27-alpine`, если его ещё нет на сервере.
Private `.env` и PostgreSQL volume сохраняются.

## Условие доставки на Dev

В каждом из четырёх GitHub-репозиториев/настроек организации должна быть
включена Actions variable:

```text
FKIT_BI_DEV_DEPLOY_ENABLED=true
```

Если значение отсутствует или не равно `true`, проверки и, для приложений,
публикация образа всё равно могут завершиться успешно, но деплой будет
пропущен. Поэтому проверяйте не только зелёный статус run, но и его summary и
шаг доставки.

При включённой доставке используются Actions variables `FKIT_BI_DEV_HOST`,
`FKIT_BI_DEV_SSH_USER`, `FKIT_BI_DEV_SSH_PORT`, `FKIT_BI_DEV_DEPLOY_PATH`,
`FKIT_BI_DEV_PUBLIC_URL` (для infra), `FKIT_BI_DEV_SSH_KNOWN_HOSTS`; secrets —
`FKIT_BI_DEV_SSH_PRIVATE_KEY` и `FKIT_BI_GITHUB_TOKEN` (для сервисных workflow).
Добавляйте их в настройки Actions, не в репозиторий и не в `.env.example`.

## Проверка результата

- В GitHub Actions откройте run соответствующего репозитория, убедитесь, что
  `verify` успешен и доставка не помечена как disabled.
- Dev: <http://45.132.176.28:8080/>.
- Health analytics: `/api/analytics/actuator/health`.
- Health generator: `/api/generator/actuator/health`.

Главная страница и оба health endpoint должны отвечать HTTP 200; backend
возвращает `status: UP`. При неуспешном run сначала изучите лог упавшего шага и
summary доставки. На сервере для диагностики используйте `docker compose ps` и
`docker compose logs --tail=100 <service>`. Не публикуйте содержимое `.env` и
не удаляйте volume командой `docker compose down -v`.
