# Story 1.2 — Infrastructure

- Compose запускает Generator только после healthy PostgreSQL и Analytics; readiness Analytics включает завершение миграций и совместимость release схемы.
- `./scripts/validate.sh` прошёл, включая изолированный preflight доставки и проверку зависимости Compose. Развёртывание не выполнялось.
