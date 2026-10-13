#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${FKIT_BOOTSTRAP_USERNAME:?FKIT_BOOTSTRAP_USERNAME должен поступить из Infisical}"
: "${FKIT_BOOTSTRAP_DISPLAY_NAME:?FKIT_BOOTSTRAP_DISPLAY_NAME должен поступить из Infisical}"
: "${FKIT_BOOTSTRAP_PASSWORD:?FKIT_BOOTSTRAP_PASSWORD должен поступить из Infisical}"
docker compose run --rm analytics-bootstrap
