# FKIT BI infrastructure

Infrastructure repository for PostgreSQL, analytics, generator, web and nginx. Analytics owns the shared database migrations.

Copy `.env.example` to `.env` only on the Dev host. Run `./scripts/validate.sh` to validate Compose and scripts. Read `docs/architecture/`, `docs/development.md`, `docs/dev-deployment.md` and `docs/bmad/project-context.md` before changing shared contracts.
