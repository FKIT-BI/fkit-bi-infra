#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
test -f .env || { echo 'Missing .env' >&2; exit 1; }
docker compose pull postgres proxy
docker compose up -d postgres proxy
