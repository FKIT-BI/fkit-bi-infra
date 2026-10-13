#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${FKIT_BOOTSTRAP_USERNAME:?FKIT_BOOTSTRAP_USERNAME must be provided by Infisical}"
: "${FKIT_BOOTSTRAP_PASSWORD:?FKIT_BOOTSTRAP_PASSWORD must be provided by Infisical}"
docker compose run --rm analytics-bootstrap reset-bootstrap-password
