# Dev delivery and recovery

Dev is `http://45.132.176.28:8080`; server configuration is `/opt/fkit-bi/.env`, mode 600, and never committed. PostgreSQL persists in the named `postgres-data` volume. Never run `docker compose down -v`.

Deliveries are serialized on the host. On failure inspect `docker compose logs`, restore a previous image reference in `.env`, then run `docker compose up -d --no-deps <service>`.
