# FKIT BI infrastructure rules

Read `docs/architecture/` and `docs/bmad/project-context.md` before planning or changing shared contracts. BMAD Core 6.12.0 is installed in the workspace root at `../_bmad`; if this repository is cloned alone, install it with `npx bmad-method@6.12.0 install --modules bmm --tools codex`.

Keep cross-service decisions and task status here. Do not put secrets in Git. Analytics alone owns Flyway migrations.
