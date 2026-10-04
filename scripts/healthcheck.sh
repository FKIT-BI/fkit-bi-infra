#!/usr/bin/env bash
set -euo pipefail
url="${1:?usage: healthcheck.sh <public-url>}"
url="${url%/}"
urls=(
  "$url/"
  "$url/api/analytics/actuator/health"
  "$url/api/generator/actuator/health"
)
for endpoint in "${urls[@]}"; do
  for attempt in $(seq 1 24); do
    if curl --connect-timeout 10 --max-time 20 --fail --silent --show-error "$endpoint" >/dev/null; then
      break
    fi
    if [[ "$attempt" == 24 ]]; then
      echo "Healthcheck failed: $endpoint" >&2
      exit 1
    fi
    sleep 5
  done
done
