# FKIT BI infrastructure

Infrastructure repository for PostgreSQL, analytics, generator, web and nginx. Analytics owns the shared database migrations.

Copy `.env.example` to `.env` only on the Dev host. Run `./scripts/validate.sh` to validate Compose and scripts. Read `docs/architecture/`, `docs/development.md`, `docs/dev-deployment.md` and `docs/bmad/project-context.md` before changing shared contracts.

Generate `FKIT_JWT_SECRET` from at least 32 cryptographically random bytes, base64-encode it, and supply it to both services through the deployment environment. After Analytics is running, set `FKIT_BOOTSTRAP_USERNAME`, `FKIT_BOOTSTRAP_DISPLAY_NAME`, and `FKIT_BOOTSTRAP_PASSWORD` outside Git and run `./scripts/bootstrap-user.sh`. The command is safe to repeat; after the first user exists it exits without changing accounts. The password is never printed.

The bootstrap credentials are passed only to the one-shot `analytics-bootstrap` container. The default Compose network uses `172.29.0.0/24`, with Nginx fixed at `172.29.0.2`; this lets Analytics trust only Nginx's overwritten client-IP header. If that subnet conflicts with the host, choose a free `COMPOSE_SUBNET`, set `PROXY_CONTAINER_IP` to an unused address inside it, and set `FKIT_TRUSTED_PROXY_CIDRS` to that Nginx address with `/32`.
