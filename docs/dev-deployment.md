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
замены `.env` и Docker volume. Скрипт не собирает и не скачивает образы, не меняет
image references, не пересоздаёт `web`; он запускает текущие сервисы и
пересоздаёт только proxy для применения nginx. В завершение из runner проверяются
`/`, `/api/analytics/actuator/health` и `/api/generator/actuator/health`.

Dev: `http://45.132.176.28:8080`. Конфигурация сервера — `/opt/fkit-bi/.env`
(режим 600, никогда не коммитится); PostgreSQL хранится в named volume
`postgres-data`. Никогда не выполняйте `docker compose down -v`.

Для первичного запуска, когда опубликованы все текущие образы, выполните на
сервере из каталога deployment:

```bash
FKIT_BI_DEV_PUBLIC_URL=http://host:port ./scripts/bootstrap-dev.sh
```

При ошибке сохраните диагностические данные командой `docker compose ps` и
`docker compose logs --tail=100 <service>`. Восстанавливайте только известную
предыдущую ссылку образа в private `.env`, затем запускайте
`docker compose up -d --no-deps <service>`; не удаляйте volume и не раскрывайте
содержимое `.env`.
