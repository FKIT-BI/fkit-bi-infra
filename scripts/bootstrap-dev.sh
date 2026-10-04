#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
test -f .env || { echo 'Missing .env' >&2; exit 1; }
docker compose pull postgres
docker compose up -d --no-build postgres analytics generator web proxy
"$(dirname "$0")/healthcheck.sh" "${FKIT_BI_DEV_PUBLIC_URL:?FKIT_BI_DEV_PUBLIC_URL is required}"
