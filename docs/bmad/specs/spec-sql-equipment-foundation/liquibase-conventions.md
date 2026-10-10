# Организация Liquibase

## Владение и расположение

Analytics — единственный владелец миграций общей PostgreSQL. Generator никогда не запускает Liquibase; таблицы `generator.*` также создаются changelog из Analytics.

```text
fkit-bi-analytics/src/main/resources/db/changelog/
├── db.changelog-master.yaml
└── releases/
    ├── 001-foundation/
    │   ├── changelog.yaml
    │   ├── 001-create-schemas.sql
    │   └── 002-create-reference-catalogs.sql
    ├── 002-equipment/
    │   ├── changelog.yaml
    │   ├── 001-create-enterprise.sql
    │   ├── 002-create-production-line.sql
    │   ├── 003-create-machine.sql
    │   ├── 004-create-component.sql
    │   ├── 005-create-telemetry-signal.sql
    │   └── 006-create-shift.sql
    ├── 003-telemetry/
    ├── 004-analytics/
    ├── 005-incidents/
    └── 006-generator/
```

`db.changelog-master.yaml` и release `changelog.yaml` используют только явные `include` в нормативном порядке. `includeAll` запрещён.

## Формат changeset

- YAML используется для композиции changelog.
- PostgreSQL DDL, индексы, partition DDL и функции оформляются Liquibase formatted SQL.
- Changeset ID имеет формат `<release>-<sequence>-<short-purpose>` и уникален во всём master; author — `fkit-bi` либо стабильный team identifier.
- Один changeset выполняет одну небольшую логическую операцию.
- Применённые changeset и seed values не редактируются; изменение добавляется следующим changeset.
- `runAlways` и `runOnChange` не используются для доменной схемы.
- Test fixtures и demo telemetry не включаются в production master.
- Tenant-specific записи `LossReason` не являются migration seed: новое Enterprise получает пустой каталог причин, а demo/test fixtures остаются вне production changelogs.
- Первая Liquibase business migration не импортирует данные из OpenAPI/UI draft. Непустая dev database не очищается автоматически; прежняя Flyway metadata остаётся без изменений.
- Rollback описывается для безопасных dev-операций; production correction опирается на forward migration, а не на разрушительный rollback.

## Spring Boot

Плановая конфигурация:

```yaml
spring:
  liquibase:
    enabled: true
    change-log: classpath:/db/changelog/db.changelog-master.yaml
```

`liquibase-core` заменяет Flyway dependencies. Context-load test отключает `spring.liquibase.enabled`; проверки реальных migrations выполняются отдельно на PostgreSQL/Testcontainers, а не H2.

Для изолированного тестового MVP Liquibase запускается автоматически при старте Analytics. Liquibase и runtime datasource используют один общий PostgreSQL account, который также использует Generator; сложная матрица owner/runtime/generator roles пока не вводится. Readiness Analytics остаётся false до полного завершения migrations. Generator запускается после Analytics readiness. Отдельный migrator container не вводится.

Liquibase поддерживает single-row `equipment.schema_release`. После migrations Analytics readiness проверяет точное ожидаемое release; Generator readiness делает ту же проверку до доступа к данным. В MVP не вводится диапазон совместимых версий: несовпадение делает приложение not-ready с явной диагностикой. Эта проверка обязательна независимо от упрощённых DB credentials.

Для тестового контура используется один общий application/development credential; он не считается production least-privilege моделью. Разделение на роли ниже отложено до появления внешних customer/production данных:

| Будущая role (не создавать в MVP) | Целевое ограничение |
| --- | --- |
| `fkit_bi_owner` | Liquibase, DDL, владение schemas и objects |
| `fkit_bi_analytics` | Runtime DML только в разрешённых schemas |
| `fkit_bi_generator` | Чтение разрешённой equipment-конфигурации, DML `generator`, append в telemetry contract |
| `fkit_bi_monitor` | Минимальный read/monitoring доступ для exporter |

## Переход с текущего bootstrap

Текущий Flyway `V1__bootstrap.sql` создаёт только `fkit_bi_schema_marker`. При реализации перехода:

1. Удалить Flyway dependencies и `spring.flyway` configuration.
2. Добавить Liquibase dependency и master changelog.
3. Не удалять автоматически существующие `flyway_schema_history` и marker table: они не конфликтуют с новыми доменными schemas.
4. На чистой базе Liquibase создаёт все schemas и собственные `DATABASECHANGELOG`/`DATABASECHANGELOGLOCK`.
5. На существующей dev-базе первый запуск проверяется отдельным migration integration test; очистка старых metadata выполняется только явной обслуживающей операцией.

Analytics считается готовым для запуска Generator только после успешного завершения Liquibase и проверки `equipment.schema_release`. Оркестрация запуска должна использовать health/readiness Analytics, а не параллельный запуск двух владельцев DDL. Удаление Flyway, добавление Liquibase и startup dependency Generator выполняются одним implementation slice. DB role separation намеренно не входит в этот slice; shared credential остаётся только для изолированного тестового стенда.
