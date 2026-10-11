# Сводка автоматизации тестов Epic 1–2

Дата: 2026-10-11

## Добавленные тесты

### API и интеграционные тесты

- [x] `AuthFlowTest` — malformed JSON, безопасный correlated error envelope, UTF-8 граница BCrypt
  и отсутствие частичной записи пользователя.
- [x] `EquipmentConfigurationApiTest` — полный конфигурационный путь AC-1, ownership,
  одноразовое назначение Machine, non-cascade статусов, readiness и атомарность ошибок
  Signal/StateConfig.
- [x] `EnterpriseShiftApiTest` — конфликтующее изменение расписания не изменяет committed Shift.

### PostgreSQL/Liquibase Testcontainers

- [x] `EpicOneMigrationContractTest` — изолированный исторический changelog Epic 1, clean/legacy
  database, повторное применение, preservation Flyway metadata и ограничения `identity.users`.
- [x] Все интеграционные классы используют реальный PostgreSQL 16 через Testcontainers; H2 для
  новых сценариев не применяется.

### UI E2E

- Не добавлялись: текущая задача ограничена Analytics API/PostgreSQL Testcontainers. Web Story 2.5
  остаётся отдельной незавершённой областью.

## Покрытие

- Новых тестовых сценариев: **8** — 4 для Epic 1 и 4 для Epic 2.
- Epic 1 regression: **35/35** тестов прошли.
- Epic 2 regression: **23/23** теста прошли.
- Итого проверено: **58** тестов, 0 failures, 0 errors, 0 skipped.
- Epic 1: application/error/trace, Liquibase ownership/readiness и Auth API.
- Epic 2: Enterprise/Shift, Line/Machine assignment, Component/Signal, StateConfig/readiness.

## Команды проверки

```text
./mvnw -B -Dtest=AnalyticsApplicationTest,LiquibaseFailureReadinessTest,DatabaseUnavailableReadinessTest,FoundationMigrationTest,EpicOneMigrationContractTest,AuthFlowTest,TraceIdFilterTest test
./mvnw -q -Dtest=EquipmentConfigurationApiTest,EnterpriseShiftApiTest,ShiftCalendarTest test
git diff --check
```

Maven-команды выполнялись в отдельных временных копиях репозитория: общий `target/` содержит
старые файлы другого владельца и не допускает безопасную перезапись из текущей sandbox-сессии.

## Обнаруженные пробелы

- Auth OpenAPI задаёт `additionalProperties: false`, однако неизвестное поле login сейчас
  игнорируется Jackson и запрос доходит до проверки credentials (`401` вместо transport-level
  `400`). Production-код не изменялся в test-only задаче.
- Эта итерация не добавляет браузерные тесты Web Story 2.5, проверки Nginx/TLS/Prometheus из Story
  1.4 или новые тесты Generator; их следует вести отдельными наборами без смешивания с Analytics
  Testcontainers suite.

## Проверка по checklist навыка

- [x] Использован существующий JUnit 5 / Spring Boot / MockMvc / Testcontainers стек.
- [x] Есть happy paths и критические `400/401/409/422` ошибки.
- [x] Нет sleeps, hardcoded waits и зависимости от порядка тестов.
- [x] Новые тесты находятся в стандартных `src/test` каталогах.
- [x] Все выбранные тесты успешно выполнены.
- [x] Сводка содержит измеримое покрытие и оставшиеся шаги.

## Следующие шаги

- Отдельно решить контрактный gap неизвестных JSON-полей Auth API.
- После завершения Web Story 2.5 добавить браузерный E2E конфигурационного пути.
- Повторить тот же Testcontainers-аудит для Epic 3–5.
