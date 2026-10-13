---
title: 'Демо-администратор: bootstrap, операторский reset и API учётных записей'
type: 'feature'
created: '2026-10-13'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '37f52225a98e42377b28bb1a1db855452b0048a9'
context:
  - 'fkit-bi-infra/docs/bmad/project-context.md'
  - 'fkit-bi-infra/docs/architecture/fkit-bi-architecture.md'
  - 'fkit-bi-infra/docs/architecture/fkit-bi-components.md'
  - 'fkit-bi-infra/docs/contracts/auth-api.yaml'
  - 'fkit-bi-infra/docs/bmad/implementation-artifacts/spec-1-3-authentication.md'
  - 'fkit-bi-infra/docs/bmad/implementation-artifacts/spec-public-swagger-for-backend-services.md'
---

<frozen-after-approval reason="user-approved test-stand onboarding intent">

## Intent

**Problem:** На тестовом стенде нет пользователей (`identity.users` пуста), поэтому фронтенд-команда не может получить JWT и проверить защищённые API. При этом публичный Swagger Analytics и Generator уже опубликован, а штатный endpoint создания пользователя требует существующий bootstrap JWT.

**Approach:** Создать первичного bootstrap-пользователя штатной одноразовой командой Analytics, сохранив его логин и пароль в указанном проекте Infisical. Если вход не проходит после provisioning, предоставить отдельную операторскую one-shot команду смены пароля только существующего bootstrap-пользователя. Затем проверить вход и существующий `POST /api/v1/auth/users` как штатный HTTP endpoint для создания обычных учётных записей; дополнить операторскую инструкцию, не добавляя публичную регистрацию или дублирующий endpoint.

## Boundaries & Constraints

**Always:** Использовать тестовый Dev-стенд `45.132.176.28`; хранить `FKIT_BOOTSTRAP_USERNAME`, `FKIT_BOOTSTRAP_DISPLAY_NAME` и `FKIT_BOOTSTRAP_PASSWORD` только в Infisical в пользовательском проекте, в пути `/github-actions`; передавать их только одноразовым операторским командам `analytics-bootstrap`; первичное создание разрешено только при пустом хранилище `identity`. Reset, если потребуется, может обновлять только BCrypt-хэш уже существующего bootstrap-пользователя и требует явной команды оператора. Сохранить защищённость бизнес-операций, право bootstrap-пользователя вызывать `POST /api/v1/auth/users`, публичность только login и Swagger-документации; не выводить пароль в логи.

**Never:** Не добавлять публичный endpoint сброса пароля или регистрации, не менять пароль обычного пользователя через bootstrap reset, не создавать bootstrap-пользователя при непустом хранилище, не менять схему БД, не трогать production и не сохранять секреты в Git. Не изменять замороженные спецификации аутентификации/Swagger и существующие незакоммиченные изменения.

## I/O & Edge-Case Matrix

| Сценарий | Вход / состояние | Ожидаемое поведение | Ошибка |
|---|---|---|---|
| Первичный запуск | Пустая `identity.users`; три bootstrap-переменные доступны оператору | One-shot `analytics-bootstrap` создаёт одну bootstrap-запись с BCrypt-хешем | Ошибка конфигурации/БД завершает команду; пароль не попадает в лог |
| Повтор bootstrap | В хранилище уже есть хотя бы один пользователь | Команда безопасно завершается no-op и не меняет пароль | Не выполнять reset через повторный запуск |
| Операторский reset | Явная reset-команда и запись целевого bootstrap-пользователя существуют | Обновляется только его BCrypt-хэш; username, display name, bootstrap marker и остальные записи неизменны | Отсутствующая или не-bootstrap учётка приводит к отказу без insert |
| Login и выдача JWT | Валидная пара bootstrap credentials | Публичный `POST /api/v1/auth/login` возвращает Bearer JWT на 1800 секунд | Неверная пара — одинаковый `401` |
| Создание обычной учётки | Bootstrap JWT и валидный `UserCreate` | Существующий `POST /api/v1/auth/users` создаёт обычного пользователя (`201`) | Без JWT — `401`, не-bootstrap — `403`, дубликат — `409` |

</frozen-after-approval>

## Code Map

- `fkit-bi-analytics/src/main/java/ru/fkit/bi/analytics/auth/BootstrapUserCommand.java` — проверяет пустую таблицу и создаёт неизменяемую bootstrap identity; повтор на непустом store ничего не меняет.
- `fkit-bi-analytics/src/main/java/ru/fkit/bi/analytics/AnalyticsApplication.java` и `BootstrapUserCommand.java` — точка подключения явной операторской команды reset, не доступной по HTTP.
- `fkit-bi-analytics/src/test/java/ru/fkit/bi/analytics/auth/AuthFlowTest.java` — контрактные проверки bootstrap, idempotence, login и create-user; дополнить проверками reset/no-insert.
- `fkit-bi-analytics/src/main/java/ru/fkit/bi/analytics/auth/AuthController.java`, `AuthService.java`, `AuthDtos.java` — уже реализованные login и bootstrap-only `POST /api/v1/auth/users`, формат ответа, права и валидация.
- `fkit-bi-analytics/docs/contracts/analytics-api-draft.yaml` — отображаемый Analytics OpenAPI с описанием и полными примерами login/create-user; не генерировать параллельный контракт.
- `fkit-bi-infra/compose.yaml`, `scripts/bootstrap-user.sh`, `README.md` — one-shot Compose service и операторский запуск; обновить только README для Infisical и последовательности демо-входа.
- `fkit-bi-infra/scripts/test-bootstrap-commands.sh`, `scripts/validate.sh` — проверить аргументы one-shot wrappers и запрет запуска без секретов.
- `fkit-bi-infra/.github/workflows/ci.yml`, `fkit-bi-analytics/.github/workflows/ci.yml` — аналитическая OIDC-доставка читает `/github-actions/analytics`, но bootstrap credentials не передаёт; текущая ручная bootstrap-команда остаётся отдельной от deploy.
- `fkit-bi-infra/docs/bmad/implementation-artifacts/spec-1-3-authentication.md` и `spec-public-swagger-for-backend-services.md` — замороженные принятые ограничения; только читать.

## Tasks & Acceptance

**Execution:**
- [x] `fkit-bi-analytics/src/main/java/ru/fkit/bi/analytics/AnalyticsApplication.java`, `auth/BootstrapUserCommand.java` — добавить отдельную операторскую reset-команду, которая требует совпадения существующего имени bootstrap-пользователя, проверяет пароль и меняет только `password_hash`; не ослаблять безопасное повторное выполнение bootstrap.
- [x] `fkit-bi-analytics/src/test/java/ru/fkit/bi/analytics/auth/AuthFlowTest.java` — проверить reset bootstrap-пользователя, отказ для отсутствующей/обычной учётки, неизменность остальных полей и отсутствие пароля в логах.
- [x] `fkit-bi-infra/scripts/reset-bootstrap-password.sh`, `scripts/bootstrap-user.sh` и `README.md` — документировать безопасные one-shot create/reset команды и полный сценарий Infisical → bootstrap/login → `POST /api/v1/auth/users`.
- [x] Infisical (проект из запроса, путь `/github-actions`) — создать логин `demo.admin`, имя `Демо-администратор` и случайный пароль допустимого формата; не записывать значение пароля в Git или лог.
- [x] Тестовый стенд `45.132.176.28` — выполнить `scripts/bootstrap-user.sh` с переменными только в одноразовом окружении; не перезапускать без необходимости long-running контейнеры.
- [x] Проверка стенда — получить JWT через login, вызвать `POST /api/v1/auth/users` с Bearer и полным DTO, проверить публичный Swagger обоих сервисов и отсутствие анонимного доступа к business API.

**Acceptance Criteria:**
- Given текущая пустая таблица `identity.users`, when оператор запускает штатный bootstrap с заданными секретами, then появляется ровно одна bootstrap-учётка, а повторный запуск не меняет её.
- Given явный operator reset для существующего bootstrap-пользователя, when команда выполняется с новым паролем, then последующий login принимает новый пароль, старый пароль отклоняется, а другие поля/учётки не меняются.
- Given bootstrap credentials, when frontend вызывает login, then получает действующий Bearer token и `canCreateUsers: true`; password/hash не возвращаются.
- Given этот token и корректный create-user payload, when вызывается документированный endpoint, then создаётся обычная учётка, доступная для последующего login.
- Given публичные адреса Swagger Analytics и Generator, when открываются без Authorization, then UI/spec возвращают HTTP 200, тогда как защищённый business API без JWT отвечает 401.

## Implementation Notes

Изменения пользователя найдены в `spec-1-3-authentication.md`, `spec-infisical-oidc-shared-identity.md` и `deferred-work.md`; их сохранить и не править. На момент расследования Analytics/Generator/infra/web находились на `develop`; `fkit-bi-analytics/.gigaide/` — существующая неотслеживаемая папка. Read-only проверка test DB вернула `0` пользователей и `0` bootstrap-пользователей. Публичные Swagger UI и YAML обоих сервисов ранее проверены HTTP 200; их отдельная спецификация уже `done`. Путь `/github-actions` выбран по предоставленной ссылке; он не является путём, который CI analytics workflow читает автоматически (`/github-actions/analytics`), поэтому значения для разового bootstrap передаются оператором, а не считаются применёнными после простого рестарта.

## Verification

**Commands:**
- `./mvnw -B verify` в Analytics — проверка регрессий auth/Swagger; учитывать документированный ранее сбой login rate-limit теста, если он воспроизведётся.
- `docker compose config -q` в infra — проверка Compose-конфигурации.
- `curl` login и create-user на тестовом Analytics URL — подтверждение токена и `201`; не печатать токен/пароль в лог.

**Manual checks:**
- В Infisical проверить наличие трёх ключей по согласованному пути, не раскрывая значения в репозитории.
- На стенде подтвердить health/readiness после one-shot provisioning и фактические HTTP-ответы Swagger UI/spec для обоих сервисов.

## Review Triage Log

- `medium / patch` — README не описывал защищённую передачу initial password обычному пользователю; добавлена передача через одобренный защищённый канал и входная проверка.
- `false` — Bootstrap-учётка задумана как операторская учётка для последующего создания пользователей; её секрет должен оставаться в Infisical, поэтому удаление или отзыв bootstrap-доступа не требуется.
- `medium / patch` — README не уточнял синхронизацию секрета после reset; теперь указано, что Infisical всегда хранит текущий пароль bootstrap-пользователя.
- `low / patch` — README не перечислял поля успешного create-user ответа; добавлены `id`, `username`, `displayName`, `createdAt` и отсутствие пароля.
- `medium / patch` — сценарий не проверял login обычной учётной записи; добавлено ожидание `200` и `canCreateUsers: false`.
- `low / patch` — не проверялись границы длины пароля reset; добавлены отказы для пароля короче 12 символов и длиннее 72 UTF-8 байт с сохранением прежнего hash.
- `low / patch` — shell-проверка не проверяла каждый отсутствующий обязательный параметр; добавлены отдельные проверки всех переменных для bootstrap/reset и запрет запуска Docker при ошибке.
- `low / patch` — shell-проверка не проверяла успешный вывод wrapper-скриптов; теперь stdout/stderr проверяются на утечку заданных credentials.
- `low / patch` — тест reset CLI передавал display name, хотя reset требует только username/password; тест теперь запускает reset без display name.
- `medium / defer` — Analytics анонимно разрешает `/actuator/info`, а внешний Nginx не блокирует этот путь; это поведение существовало до текущей реализации, поэтому его проверка и ограничение маршрута вынесены в `deferred-work.md`.

**Результаты текущего выполнения:** Analytics `./mvnw -B verify` — BUILD SUCCESS, 80 тестов прошли, включая reset/no-insert и проверку отсутствия нового пароля в логах. `docker compose --env-file .env.example config --quiet`, `bash -n scripts/bootstrap-user.sh scripts/reset-bootstrap-password.sh` и `git diff --check` прошли. В Infisical `dev:/github-actions` через Universal Auth созданы три bootstrap-секрета. На `45.132.176.28` one-shot bootstrap создал ровно одну bootstrap-учётку без перезапуска долгоживущих контейнеров; live login вернул `200`, JWT на 1800 секунд и `canCreateUsers: true`. Авторизованный `POST /api/v1/auth/users` вернул `201`, а вход созданного `demo.frontend` — `200` и `canCreateUsers: false`. Оба Swagger UI и оба YAML вернули HTTP 200; анонимный `POST /api/v1/auth/users` — 401. Полная `scripts/validate.sh` остановилась на отсутствующем в host Python-модуле `openapi_spec_validator` после успешной runtime-contract проверки.
