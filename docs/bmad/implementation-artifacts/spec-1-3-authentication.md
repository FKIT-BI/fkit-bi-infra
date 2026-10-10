---
title: '1.3 — Аутентификация и учётные записи'
type: 'feature'
created: '2026-10-10'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: 'a52c1f0c77825fd7a195f0a0cc39b1b8045a75ae'
context:
  - 'fkit-bi-infra/docs/contracts/auth-api.yaml'
  - 'fkit-bi-infra/docs/bmad/specs/spec-security-audit/SPEC.md'
  - 'fkit-bi-infra/docs/bmad/specs/spec-security-audit/security-and-deployment.md'
  - 'fkit-bi-infra/docs/bmad/implementation-artifacts/epic-1-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Analytics и Generator пока не защищают бизнес API, а MVP требует общего входа и минимального управления учётными записями без сложной матрицы ролей.

**Approach:** Analytics хранит пользователей, выполняет вход и выпускает короткоживущий JWT; Analytics и Generator одинаково валидируют токен. Первый bootstrap-пользователь создаётся оператором одноразовой командой, затем только он может создавать обычных пользователей через отдельный auth API.

## Boundaries & Constraints

**Always:** Реализовать ровно контракт `docs/contracts/auth-api.yaml`: публичный `POST /api/v1/auth/login`, защищённый `POST /api/v1/auth/users`, указанные DTO, статусы, ошибки и лимиты. JWT HS256, issuer `fkit-bi`, audience `fkit-bi-api`, `sub` — UUID пользователя, `iat`, `exp`, срок 1800 секунд; без refresh и role claims. Пароли хранить только BCrypt-хэшами; username нормализовать в нижний регистр и обеспечить уникальность. Bootstrap-признак хранится неизменяемо в БД и проверяется сервером, а не берётся из JWT. Rate limit: 10 login/min на доверенный IP и 5 create/min для bootstrap-user; переданный клиентом IP не считать доверенным без настроенного reverse proxy. Исключить из bearer-защиты только health/liveness/readiness и внутренние actuator endpoints, необходимые probes/monitoring; все бизнес API и прочие публичные операции защищены. Analytics остаётся единственным владельцем Liquibase; добавить append-only миграцию `002-authentication`, не редактировать `001-foundation`. Добавить логическую схему `identity` для пользователей и обновить точное значение schema release на `002-authentication` в обеих службах. Секрет подписи JWT поступает извне, не хранится в БД, git или образах.

**Never:** Не добавлять роли/права на предприятия, refresh tokens, восстановление пароля, MFA, публичную регистрацию, физическое удаление/отключение пользователей, отдельный auth-сервис или вторую БД. Generator не выпускает JWT, не хранит пользователей и не выполняет DDL. Не менять существующие данные или уже применённый changeset.

## I/O & Edge-Case Matrix

| Сценарий | Вход / состояние | Ожидаемое поведение | Ошибка |
|---|---|---|---|
| Первый запуск | Bootstrap-команда и пустое хранилище пользователей | Создаёт единственного bootstrap-user; повторный запуск не меняет данные | Секрет не выводится в лог; ошибка миграции/БД завершает команду неуспешно |
| Login | Валидные credentials | `200`, Bearer token на 1800 секунд и безопасный user DTO | Неверные username/password дают одинаковый `401`; лимит даёт `429`/`Retry-After` |
| Создание пользователя | Bearer bootstrap-user и валидный DTO | `201`, Location и user DTO без пароля/хэша | Обычный пользователь получает `403`, дублирующий username — `409`, invalid fields — `422` |
| Доступ к API | Неточный, истёкший, чужого issuer/audience или отсутствующий JWT | Analytics и Generator отклоняют business request | `401` в общей форме ошибки; health probes продолжают работать без JWT |

</frozen-after-approval>

## Code Map

- `fkit-bi-infra/docs/contracts/auth-api.yaml` — нормативные endpoints, DTO, лимиты, JWT claims и ошибки; реализация должна соответствовать без изменения контракта.
- `fkit-bi-analytics/src/main/java/ru/fkit/bi/analytics/api/` — переиспользовать trace ID и error envelope; добавить auth adapter/config, не ломая Actuator и readiness.
- `fkit-bi-analytics/src/main/resources/db/changelog/` — единственная точка Liquibase; добавить новый release, оставить `001-foundation` неизменным.
- `fkit-bi-generator/src/main/java/ru/fkit/bi/generator/` — добавить только JWT resource-server validation; не добавлять endpoints/DDL.
- `fkit-bi-analytics/pom.xml`, `fkit-bi-generator/pom.xml` — существующая Java 21 / Boot 3.5.16 сборка; добавить согласованные security/JWT зависимости.
- `fkit-bi-analytics/src/test/java/` и `fkit-bi-generator/src/test/java/` — использовать существующий JUnit/Testcontainers PostgreSQL паттерн; не подменять PostgreSQL на H2.
- `fkit-bi-infra/docs/architecture/` — уточнить auth module/schema ownership и API edge после реализации, не менять инфраструктурную публикацию Story 1.4.

## Tasks & Acceptance

**Execution:**
- [x] `fkit-bi-analytics/src/main/resources/db/changelog/` — создать `identity` и таблицу пользователей через Liquibase `002-authentication`, уникальный нормализованный username и один bootstrap marker; обновить ожидаемый schema release.
- [x] `fkit-bi-analytics/src/main/java/ru/fkit/bi/analytics/` — реализовать password hashing, безопасную одноразовую bootstrap-команду, login, bootstrap-only user creation, JWT issue/validation, rate limits и контрактные ошибки.
- [x] `fkit-bi-generator/src/main/java/ru/fkit/bi/generator/` — валидировать общий JWT на всех business endpoints; сохранить unauthenticated probes.
- [x] `fkit-bi-analytics/pom.xml`, `fkit-bi-generator/pom.xml`, `fkit-bi-infra/` — подключить security dependencies/config/secrets и регрессионные тесты, сохранив compose readiness.
- [x] `fkit-bi-infra/docs/architecture/` — согласовать архитектурные ограничения со схемой `identity` и общей JWT границей.

**Acceptance Criteria:**
- Given пустая PostgreSQL, when Analytics применяет Liquibase и bootstrap-команда запускается дважды, then schema release `002-authentication` готов, создан один bootstrap-user и повтор не изменяет его.
- Given валидный auth API запрос, when создаётся пользователь или выполняется login, then ответы и ошибки соответствуют OpenAPI, секреты отсутствуют в ответах/логах, лимиты применяются.
- Given валидный/невалидный/истёкший JWT, when клиент обращается к любому business API Analytics или Generator, then оба сервиса согласованно принимают/отклоняют его, сохраняя доступность health probes.
- Given чистая и существующая БД, when Testcontainers применяет миграции, then все прежние foundation/legacy данные сохранены, а повторная миграция идемпотентна.

## Implementation Notes

Планировочное решение: выделить `identity` как шестую логическую схему вместо размещения пользователей в `equipment`; это сохраняет границу доменов. Совместимый release меняется на `002-authentication`, иначе Generator не сможет распознать добавленную схему. Ограничение rate limit реализовать простым локальным механизмом для текущего single-instance MVP с явно документированным reset при перезапуске; не добавлять новую БД/распределённую очередь. Bootstrap-команду запускать в non-web режиме с credentials из deployment environment и безопасным no-op, если пользовательский store уже инициализирован.

Сеть Compose резервирует отдельный IP proxy; при смене `COMPOSE_SUBNET` необходимо задать `PROXY_CONTAINER_IP` внутри подсети и согласованный `FKIT_TRUSTED_PROXY_CIDRS`. Bootstrap credentials доступны только профилю одноразового контейнера. Финальная проверка: Analytics — 27 тестов, Generator — 16 тестов, `fkit-bi-infra/scripts/validate.sh` — exit 0.

## Spec Change Log

## Review Triage Log

- `medium / patch` — Invalid login fields returned 422 despite the login contract listing 400; Analytics now maps login DTO violations to the shared 400 envelope, covered by `loginFieldValidationUsesContractBadRequestStatus`.
- `medium / patch` — Bootstrap credentials were present in the long-running Analytics container; moved them to the one-shot `analytics-bootstrap` Compose service.
- `medium / patch` — Empty proxy CIDRs grouped Nginx clients into one rate-limit key; Nginx now has a fixed Compose IP and Analytics trusts only that `/32` by default.
- `medium / patch` — A burst of distinct IPs could grow the local limiter map without bound during one minute; the limiter now caps tracked clients and rejects new keys until window rollover.
- `medium / patch` — JWT validators accepted future `iat` and lifetimes above 1800 seconds; both services now enforce issued-at and maximum lifetime.
- `medium / patch` — Forwarded IP parsing could resolve hostnames; it now accepts only IPv4/IPv6 literals.
- `medium / patch` — A stale signed bootstrap subject could turn user creation into 500; absent database subjects now receive 403.
- `medium / patch` — Trusted-proxy extraction and the documented bootstrap CLI path lacked coverage; added configured-proxy rate-limit assertions and an end-to-end `main` dispatch/repeat test.
- `false` — The fixed-window limiter can admit adjacent-minute bursts, but the spec explicitly chooses a simple local per-minute mechanism and does not require a rolling window.
- `false` — The bootstrap command's initial count duplicates its locked check, but the first check enables a safe repeat no-op without requiring secrets, while the second check closes the concurrent-initialization race.
- `false` — `Location` has no corresponding GET route, but the normative contract requires a URI-reference header and defines no user-read endpoint.

## Verification

**Commands:**
- `./mvnw -B verify` в Analytics и Generator — ожидаются unit и PostgreSQL Testcontainers тесты.
- `./scripts/validate.sh` в `fkit-bi-infra` — ожидается успешная проверка конфигурации/маршрутов без публикации.

**Manual checks:** OpenAPI auth contract diff отсутствует; все защищённые business API закрыты без JWT, health probes остаются открыты; секреты не появляются в логах, образах и git.
