#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
test -f .env || { echo 'Missing .env' >&2; exit 1; }
grafana_password="$(docker compose config --environment | sed -n 's/^GRAFANA_ADMIN_PASSWORD=//p' | tail -n 1)"
if [[ "$grafana_password" == \"*\" && "$grafana_password" == *\" ]]; then
  grafana_password="${grafana_password:1:${#grafana_password}-2}"
elif [[ "$grafana_password" == \'*\' && "$grafana_password" == *\' ]]; then
  grafana_password="${grafana_password:1:${#grafana_password}-2}"
fi
case "$grafana_password" in
  ''|replace-with-secret|replace-with-a-grafana-secret)
    echo 'Set a non-placeholder GRAFANA_ADMIN_PASSWORD in .env.' >&2
    exit 1
    ;;
esac
docker compose up -d
"$(dirname "$0")/healthcheck.sh" "${FKIT_BI_DEV_PUBLIC_URL:?FKIT_BI_DEV_PUBLIC_URL is required}"
