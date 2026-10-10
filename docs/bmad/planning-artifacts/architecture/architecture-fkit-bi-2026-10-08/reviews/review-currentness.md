# Reviewer Gate — currentness / reality

Дата проверки: 2026-10-09  
Артефакт: `ARCHITECTURE-SPINE.md`  
Линза: актуальность стека, совместимость технологий, реальность относительно текущего репозитория и эксплуатационные особенности PostgreSQL partition DDL.

## Verdict

**CHANGES REQUIRED.** Целевая комбинация Java 21 + Spring Boot 3.5 + Liquibase + PostgreSQL 16 совместима, а базовая модель суточных partitions разумна. Однако spine пока нельзя считать согласованным с фактическим brownfield-состоянием: приложение всё ещё запускает Flyway, Compose нарушает принятые правила владения и порядка запуска, а критически важный способ безопасного создания/удаления partitions не закреплён. Это не требует смены общей архитектуры, но требует уточнения spine и обязательных implementation-readiness задач до включения ingestion.

## Что подтверждено

| Утверждение spine | Результат проверки |
| --- | --- |
| Java 21 совместима со Spring Boot 3.5 | Подтверждено. Текущая ветка Spring Boot 3.5 требует Java 17+ и поддерживает Java до 25 включительно; Java 21 остаётся LTS. Текущие Dockerfiles действительно собирают и запускают приложение на Eclipse Temurin 21. |
| Spring Boot 3.5.0 управляет Liquibase 4.31.1 | Подтверждено по официальному BOM тега `v3.5.0`. |
| Spring Boot 3.5.0 управляет PostgreSQL JDBC 42.7.5 | Подтверждено по официальному BOM тега `v3.5.0`. |
| PostgreSQL 16 пригодна для решения | Подтверждено. Ветка поддерживается до 2028-11-09; на дату проверки актуальный minor — 16.15. Compose использует major-floating тег `postgres:16-alpine`. |
| Liquibase 4.31.1 всё ещё применима | Да, но версия уже superseded. Она остаётся управляемой даже Spring Boot 3.5.16; официальный lifecycle Liquibase указывает срок поддержки 4.31.1 до 2027-02-17. Переход на Liquibase 6 для MVP не нужен без отдельной миграционной проверки. |
| Суточное `RANGE(observed_at)` и отсутствие default partition | Поддерживается PostgreSQL 16 и соответствует заявленному fail-fast поведению: insert без подходящей partition завершится ошибкой. |

## Findings

### HIGH-1 — Spine выдаёт Liquibase за принятый runtime-инвариант, но фактический Analytics продолжает запускать Flyway

**Evidence.** В spine AD-2 и Stack закрепляют Liquibase. В текущем репозитории:

- [`fkit-bi-analytics/pom.xml`](../../../../../../../../fkit-bi-analytics/pom.xml) содержит `flyway-core` и `flyway-database-postgresql`, но не `liquibase-core`;
- [`fkit-bi-analytics/src/main/resources/application.yml`](../../../../../../../../fkit-bi-analytics/src/main/resources/application.yml) содержит `spring.flyway.enabled: true`;
- единственный migration-файл — `src/main/resources/db/migration/V1__bootstrap.sql`; плановой папки `db/changelog/` пока нет;
- корневое правило [`fkit-bi-infra/AGENTS.md`](../../../../../../AGENTS.md) всё ещё говорит, что Analytics владеет Flyway, хотя `fkit-bi-analytics/AGENTS.md` уже говорит о Liquibase.

Это известный переходный долг в spec, но сам spine не маркирует его как неисполненный prerequisite. Для brownfield-документа различие между «архитектурно принято» и «уже реально действует» должно быть явным.

**Impact.** Builder может считать Liquibase готовой основой, добавить changelog и получить одновременную автоконфигурацию двух migration engines или неверные readiness-тесты.

**Required action.** Либо добавить в spine отдельный `Implementation prerequisite`/`Reality gap` для атомарной замены Flyway на Liquibase, либо не помечать AD-2 как фактически реализованный. Acceptance перехода: в runtime classpath нет Flyway, `spring.flyway` отсутствует, Liquibase master существует, context test отключает `spring.liquibase`, migration integration test выполняется на PostgreSQL, а устаревшее правило в infra `AGENTS.md` исправлено.

### HIGH-2 — Фактический Compose нарушает AD-2 и AD-11: оба сервиса работают одним владельцем БД и Generator не ждёт migrations

**Evidence.** В [`fkit-bi-infra/compose.yaml`](../../../../../../compose.yaml):

- Analytics и Generator получают одинаковые `${POSTGRES_USER}` / `${POSTGRES_PASSWORD}`;
- этот же пользователь создаёт базу и практически является владельцем объектов;
- оба сервиса зависят только от `postgres: service_healthy`;
- Generator не зависит от readiness Analytics или отдельного migration job.

Это прямо расходится с AD-2 (migrations должны завершиться до Generator) и AD-11 (отдельные credentials и least privilege).

**Impact.** При реальном внедрении Liquibase Generator способен стартовать на частично мигрированной схеме; компрометация Generator даёт DDL/owner-доступ; интеграционные тесты не проверяют реальную модель grants.

**Required action.** До первого доменного migration добавить bootstrap ролей и раздельные secrets/переменные. Analytics runtime и Liquibase должны также иметь раздельные credentials, если AD-11 понимается буквально. Startup должен быть одним из двух явно выбранных вариантов:

1. одноразовый migration service успешно завершается, затем стартуют Analytics и Generator; либо
2. Analytics применяет Liquibase, его readiness сигнализирует `schema-ready`, Generator зависит от этого readiness, а не только от PostgreSQL.

### HIGH-3 — AD-10 не закрепляет lock-safe partition DDL и не определяет исполнителя с нужными правами

**Evidence.** Spine требует заранее создавать partitions и запрещает runtime credentials выполнять DDL, но не отвечает, кто и каким SQL создаёт/удаляет ежедневные partitions. Это существенный пробел, потому что PostgreSQL 16 использует разные lock modes:

- `CREATE TABLE ... PARTITION OF` требует `ACCESS EXCLUSIVE` на parent и способен блокировать concurrent inserts;
- создание standalone table с подходящим `CHECK`, локальным индексом и последующий `ATTACH PARTITION` требует только `SHARE UPDATE EXCLUSIVE` на parent; валидный `CHECK` устраняет validation scan;
- обычный `DETACH PARTITION` использует сильную блокировку; `DETACH PARTITION ... CONCURRENTLY` снижает lock level, но выполняет две внутренние транзакции, не допускается внутри transaction block и требует ownership parent/child;
- текущий запрет default partition как раз совместим с `DETACH ... CONCURRENTLY`.

Официальная документация: [PostgreSQL 16 partition maintenance](https://www.postgresql.org/docs/16/ddl-partitioning.html#DDL-PARTITIONING-MAINTENANCE), [ALTER TABLE ATTACH/DETACH](https://www.postgresql.org/docs/16/sql-altertable.html).

**Impact.** Наивная реализация scheduler через `CREATE TABLE ... PARTITION OF` или owner-less runtime функцию либо не заработает, либо создаст именно ту блокировку ingestion, которую AD-10 должен предотвращать. `DETACH ... CONCURRENTLY` нельзя спрятать в обычную транзакционную Liquibase/PL/pgSQL-функцию.

**Required action.** Закрепить один исполнимый protocol как архитектурный инвариант:

- create: standalone child `LIKE parent INCLUDING ...` → точный UTC `CHECK` → локальный `(signal_id, observed_at)` index → `ATTACH PARTITION`; advisory lock и идемпотентная проверка имени/bounds;
- retention: `DETACH PARTITION ... CONCURRENTLY` через autocommit maintenance connection/job, затем отдельный `DROP TABLE`, либо для MVP обычный detach с коротким `lock_timeout` и retry — выбор должен быть явным;
- ownership: отдельная maintenance role, которой принадлежат parent/child, либо минимальная owner-owned `SECURITY DEFINER` поверхность с фиксированным `search_path`, отзывом `PUBLIC EXECUTE` и строгой валидацией идентификаторов. При concurrent detach всё равно нужен вызывающий контур вне transaction block.

### MEDIUM-1 — Версии совместимы, но Spring Boot и JDBC зафиксированы на устаревших patch-релизах

**Evidence.** Официальная актуальная документация ветки 3.5 на дату проверки показывает Spring Boot 3.5.16. Репозиторий и spine используют 3.5.0. Официальный BOM:

- `v3.5.0`: Liquibase 4.31.1, PostgreSQL JDBC 42.7.5;
- `v3.5.16`: Liquibase 4.31.1, PostgreSQL JDBC 42.7.11.

Источники: [Spring Boot 3.5 system requirements](https://docs.spring.io/spring-boot/3.5/system-requirements.html), [Spring Boot releases](https://github.com/spring-projects/spring-boot/releases), [BOM v3.5.0](https://github.com/spring-projects/spring-boot/blob/v3.5.0/spring-boot-project/spring-boot-dependencies/build.gradle), [BOM v3.5.16](https://github.com/spring-projects/spring-boot/blob/v3.5.16/spring-boot-project/spring-boot-dependencies/build.gradle).

**Impact.** Архитектурной несовместимости нет, но начало новой реализации на первом patch-релизе ветки оставляет исправления framework/JDBC за бортом. Указание `Liquibase 4.31.1 (Spring Boot 3.5.0 managed)` верно, но создаёт ложное впечатление, что именно Boot 3.5.0 является требуемой базой.

**Required action.** До implementation baseline обновить оба сервиса синхронно на актуальный протестированный patch ветки 3.5 (сейчас 3.5.16), принять managed JDBC и оставить Liquibase под BOM. Не переходить на Spring Boot 4 или Liquibase 6 в рамках этой задачи.

### MEDIUM-2 — Major-floating container tags не обеспечивают воспроизводимость заявленного Stack

**Evidence.** Compose использует `postgres:16-alpine`, Dockerfiles — `maven:3.9.11-eclipse-temurin-21` и `eclipse-temurin:21-jre-alpine`. При повторном pull содержимое runtime меняется без изменения Git. PostgreSQL 16 как major остаётся поддерживаемым, и PostgreSQL рекомендует актуальный minor; Java 21 также остаётся LTS. Проблема не в совместимости, а в воспроизводимости demo/deployment.

Источники: [PostgreSQL versioning policy](https://www.postgresql.org/support/versioning/), [Oracle Java SE support roadmap](https://www.oracle.com/java/technologies/java-se-support-roadmap.html).

**Impact.** Два развёртывания одного commit могут получить разные minor/JRE image и разные исправления. Это усложняет benchmark и разбор регрессий.

**Required action.** Для local development major-floating tags допустимы. Для benchmark/dev-delivery фиксировать resolved image digest либо exact patch tag в release environment и публиковать его вместе с git SHA. Java 21 менять на 25 не требуется; текущий Eclipse Temurin не наследует специфичную лицензию Oracle JDK.

## Рекомендуемая итоговая формулировка stack policy

Вместо фиксации старого patch как архитектурного инварианта:

```text
Java: 21 LTS, Eclipse Temurin runtime
Spring Boot: 3.5.x, один и тот же проверенный current patch во всех Java-сервисах
Liquibase: managed by Spring Boot BOM; baseline 4.31.1
PostgreSQL: major 16, актуальный поддерживаемый minor; release image фиксируется digest
PostgreSQL JDBC: managed by Spring Boot BOM
```

Это сохраняет совместимость и одновременно не превращает spine в быстро устаревающий dependency lockfile.

## Источники и ограничения проверки

- [Spring Boot 3.5 system requirements](https://docs.spring.io/spring-boot/3.5/system-requirements.html)
- [Spring Boot 3.5 release notes](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.5-Release-Notes)
- [Spring Boot BOM v3.5.0](https://github.com/spring-projects/spring-boot/blob/v3.5.0/spring-boot-project/spring-boot-dependencies/build.gradle)
- [Spring Boot BOM v3.5.16](https://github.com/spring-projects/spring-boot/blob/v3.5.16/spring-boot-project/spring-boot-dependencies/build.gradle)
- [Liquibase 4.31.1 release notes](https://docs.liquibase.com/pro/release-notes/4-31-1)
- [Liquibase supported versions](https://docs.liquibase.com/secure/supported-versions)
- [PostgreSQL 16 partitioning](https://www.postgresql.org/docs/16/ddl-partitioning.html)
- [PostgreSQL 16 ALTER TABLE](https://www.postgresql.org/docs/16/sql-altertable.html)
- [PostgreSQL versioning policy](https://www.postgresql.org/support/versioning/)
- [Oracle Java SE support roadmap](https://www.oracle.com/java/technologies/java-se-support-roadmap.html)

Локальный Maven dependency tree не был выполнен: в текущей shell-среде `JAVA_HOME` не указывает на рабочий JDK. Это не влияет на проверку declared POM/BOM: managed versions подтверждены напрямую официальными BOM соответствующих Spring Boot tags. Runtime/DDL поведение самой ещё не реализованной схемы проверить невозможно; findings выше являются readiness conditions для её реализации.
