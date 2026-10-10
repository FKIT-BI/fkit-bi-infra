---
title: '1.2 — Владение миграциями PostgreSQL и готовность схемы'
type: 'feature'
created: '2026-10-10'
status: 'done'
baseline_commit: '174d379605d868230b058f65846b6af482fb2939'
route: 'dispatch'
review_loop_iteration: 0
context:
  - 'fkit-bi-infra/docs/bmad/implementation-artifacts/epic-1-context.md'
  - 'fkit-bi-infra/docs/bmad/specs/spec-sql-equipment-foundation/liquibase-conventions.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Analytics использует Flyway bootstrap, а Generator не проверяет совместимость схемы; переход не определён для чистой и существующей dev-БД.

**Approach:** Передать миграции общей PostgreSQL Analytics через Liquibase; readiness обеих служб зависит от точного release схемы. Generator запускается после готовности Analytics.

## Boundaries & Constraints

**Always:** Analytics автоматически запускает Liquibase 4.31.1; Generator DDL не выполняет. Общие настройки: PostgreSQL 16, Spring Boot 3.5.16, JDBC и единый DB account. Changelog — явные includes (без `includeAll`, `runAlways`, `runOnChange`). Обе службы проверяют единственный `equipment.schema_release=001-foundation`. Создаются пять схем, marker и согласованные справочники; начальный `measurement_unit`: `PCS`, `METER`, `KILOGRAM`, `LITER`, `CELSIUS`, `PERCENT`, `RPM`, `BAR`. Остальные таблицы принадлежат будущим migrations. Не менять/не очищать существующие `flyway_schema_history`, `fkit_bi_schema_marker` и данные. Ошибка migration/DB/release делает readiness DOWN с безопасной диагностикой; liveness независим. SQL-тесты используют PostgreSQL Testcontainers, не H2.

**Never:** Не вводить migrator/DB roles, не менять deployment, не удалять legacy data, не загружать demo/tenant data и не создавать доменные таблицы сверх foundation.

## I/O & Edge-Case Matrix

| Сценарий | Вход / состояние | Ожидаемое поведение | Ошибка |
|---|---|---|---|
| Чистая БД | Analytics стартует без схем | Liquibase создаёт основу и release `001-foundation`; повторный update не меняет её | Неуспешная миграция оставляет Analytics неготовым |
| Существующая dev-БД | Есть marker row и Flyway history | Liquibase применяется независимо; старые таблица и строки остаются неизменными | Никакой автоматической очистки/переноса |
| Readiness | Release отсутствует, отличается или БД недоступна | Analytics и Generator DOWN; точное совпадение даёт UP | Liveness не становится DOWN только из-за readiness |
| Порядок запуска | Compose запускает Generator | Generator ждёт healthy Analytics и PostgreSQL | Не запускать Generator против незавершённых миграций |

</frozen-after-approval>

## Code Map

- Analytics `pom.xml`, `application.yml`, `db/migration/V1__bootstrap.sql` — заменить Flyway, сохранив DB objects.
- Оба `*Application.java`/`application.yml` — readiness groups Story 1.1; добавить JDBC indicators. Generator `pom.xml` — только test support; `telemetry/JdbcTelemetrySink` не менять.
- Infra `compose.yaml` — добавить Analytics dependency. SQL/seed нормативны в `spec-sql-equipment-foundation/{liquibase-conventions.md,schema-model.md,integrity-and-indexes.md}` и `spec-telemetry-signal/signal-model.md`; test standard — `spec-mvp-acceptance-strategy/test-strategy.md`.

## Tasks & Acceptance

**Execution:**

- [x] Analytics `pom.xml`, `application.yml`, `db/` — заменить Flyway на явный Liquibase master/`001-foundation`; удалить старый SQL-файл, не DB objects.
- [x] Foundation SQL — пять схем, `equipment.schema_release`, `signal_semantic` с нормативными codes и `measurement_unit` согласно ответу.
- [x] Analytics/Generator health packages и config — точный JDBC release check; Compose — Generator ждёт healthy Analytics и PostgreSQL.
- [x] Оба backend: Testcontainers для clean/legacy migration, preservation, idempotency, release match/mismatch/missing и migration/database failure readiness; `verify` + infra validate, evidence в `docs/tasks/`.

**Acceptance Criteria:**

- Given чистая PostgreSQL 16, when Analytics повторно применяет Liquibase, then пять схем и marker `001-foundation` идемпотентны, readiness UP.
- Given legacy Flyway history и marker row, when Liquibase применяется, then foundation создан, legacy data неизменна.
- Given DB недоступна, release отсутствует/отличается, when проверяется readiness, then обе службы DOWN безопасно; точный release даёт UP, Generator DDL не выполняет.
- Given Compose стартует, when Analytics/PostgreSQL не healthy, then Generator ждёт и стартует после migration.

## Implementation Notes

- Analytics автоматически применяет Liquibase при старте; ошибка фиксируется безопасным статусом `MIGRATION_FAILED`, приложение остаётся доступно для health endpoint, но readiness DOWN. Generator остаётся заблокирован на healthy-зависимости. Readiness выполняет один release/connectivity check; ожидание получения JDBC-соединения ограничено 2 секундами.

## Spec Change Log

## Review Triage Log

- Blind Hunter — глобальная публикация деталей health раскрывала служебные сведения вне readiness — **medium**, дефект подтверждён; исправлено: детали скрыты по умолчанию и доступны только в readiness, есть проверка общего health endpoint.
- Blind Hunter — миграционный тест не закреплял полный набор кодов каталогов — **medium**, подтверждено; исправлено точными множествами semantic и unit codes и проверкой unit mapping.
- Verification Gap — тот же пробел фиксации кодов справочников — **medium**, подтверждено; исправление общее с предыдущей записью и проверяется тем же тестом.
- Blind Hunter — не проверялись ограничения status и единственной строки schema release — **medium**, подтверждено; исправлено проверками недопустимого status, `singleton=false` и повторной `singleton=true`.
- Blind Hunter — legacy fixtures были непохожи на структуру marker/Flyway metadata и имели по одной записи — **medium**, подтверждено; исправлено fixture с исходной структурой marker, типичными полями Flyway и двумя сохранёнными строками каждого объекта.
- Verification Gap — Compose dependency Generator→Analytics не проверялась регрессией — **medium**, подтверждено; исправлено assertion в `test-delivery.sh`, infra validation проходит.
- Edge Case Hunter — при ошибке Liquibase HTTP health endpoint недоступен из-за прерывания boot — **medium**, дефект подтверждён; исправлено: конфигурация сохраняет безопасное состояние migration failure, а readiness возвращает DOWN `MIGRATION_FAILED`, проверено падающим changeset на PostgreSQL.
- Blind Hunter — тот же сценарий ошибки Liquibase и readiness — **medium**, общий корень и исправление с предыдущей записью; failure path покрыт тем же Testcontainers тестом.
- Blind Hunter — отдельный интеграционный тест, соединяющий migration Analytics и Generator readiness, отсутствовал — **false**: migration проверяется на PostgreSQL в Analytics, а Generator проверяет ту же таблицу/колонки реальным JDBC-запросом на PostgreSQL; Compose связывает сервисы по readiness.
- Blind Hunter — seed values не были продублированы в документации рядом с changelog — **false**: нормативные semantic codes уже хранятся в linked `signal-model.md`, unit codes закреплены в замороженной части spec; regression test теперь сравнивает миграцию с точными наборами.

## Verification

**Commands:**

- `./mvnw verify` в обоих backend repositories — ожидается успешный полный набор unit и PostgreSQL Testcontainers tests.
- `./scripts/validate.sh` в `fkit-bi-infra` — ожидается корректный Compose dependency graph и сохранение проверок доставки без deploy.

**Результат:** `verify` Analytics пройден (17 тестов); `verify` Generator пройден (15 тестов); infra validation пройдена. Для сборок использован временный каталог, потому что существующие Maven `target/` принадлежат root.
