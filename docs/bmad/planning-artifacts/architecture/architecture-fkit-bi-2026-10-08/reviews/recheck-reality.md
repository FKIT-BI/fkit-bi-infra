# Recheck — currentness / brownfield reality

Дата: 2026-10-09  
Артефакт: `ARCHITECTURE-SPINE.md`

## Verdict

**PASS WITH IMPLEMENTATION CONDITIONS.** Spine теперь пригоден как target architecture: Java 21 + Spring Boot 3.5.16 + Liquibase 4.31.1 + PostgreSQL JDBC 42.7.11 совместимы, PostgreSQL 16 поддерживается до 2028-11-09, embedded Liquibase до готовности Analytics и обычный partition detach с коротким timeout являются достаточным упрощённым MVP-протоколом. Текущий Flyway-код не опровергает spine, потому что это явно ещё не реализованный target.

## Findings

### MEDIUM-1 — Переход Flyway → Liquibase и новый startup order должны быть одним implementation slice

Сейчас Analytics всё ещё использует Spring Boot 3.5.0, Flyway и `spring.flyway`; Compose выдаёт Analytics и Generator одни credentials и запускает оба после одной лишь готовности PostgreSQL. Кроме того, `fkit-bi-infra/AGENTS.md` всё ещё называет владельцем миграций Flyway. Это допустимый brownfield gap, но нельзя внедрять его частями: одна задача должна одновременно удалить Flyway, добавить Liquibase и owner credentials, перевести оба сервиса на 3.5.16, разделить runtime credentials и поставить Generator после health/readiness Analytics. Иначе возможны два migration engine либо старт Generator на неполной схеме.

### MEDIUM-2 — Короткий DDL timeout должен распространяться и на создание partition

AD-10 явно задаёт timeout/retry для ordinary detach, но не так же явно для create/attach. Простая MVP-реализация может оставить `CREATE TABLE ... PARTITION OF`, поскольку partition создаётся заранее, однако вызов обязан использовать короткие `lock_timeout` и `statement_timeout`: ожидающий `ACCESS EXCLUSIVE` способен поставить горячие inserts в очередь. При timeout задача откладывается и повторяется; создание partition внутри TelemetrySink запрещено. Более сложный standalone-table + attach protocol до benchmark не требуется.

## Currentness evidence

- Spring Boot 3.5.16 поддерживает Java 17–25: <https://docs.spring.io/spring-boot/3.5/system-requirements.html>
- BOM Spring Boot 3.5.16 управляет Liquibase 4.31.1 и PostgreSQL JDBC 42.7.11: <https://docs.spring.io/spring-boot/3.5/appendix/dependency-versions/coordinates.html>
- Embedded Liquibase выполняется при startup и может использовать отдельные `spring.liquibase.url/user/password`: <https://docs.spring.io/spring-boot/3.5/how-to/data-initialization.html>
- PostgreSQL 16.15 поддерживается до 2028-11-09: <https://www.postgresql.org/support/versioning/>

