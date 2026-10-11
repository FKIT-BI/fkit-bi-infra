#!/usr/bin/env bash
set -euo pipefail
if (( $# != 1 && $# != 3 )); then
  echo 'usage: healthcheck.sh <public-url> [<analytics-url> <generator-url>]' >&2
  exit 2
fi

url="$1"
url="${url%/}"
if (( $# == 3 )); then
  urls=(
    "$url/"
    "$url/api/analytics/actuator/health"
    "$url/api/generator/actuator/health"
    "$2"
    "$3"
  )
else
  urls=(
    "$url/"
    "$url/api/analytics/actuator/health"
    "$url/api/generator/actuator/health"
  )
fi
body_file="$(mktemp)"
trap 'rm -f "$body_file"' EXIT
for endpoint in "${urls[@]}"; do
  for attempt in $(seq 1 24); do
    : > "$body_file"
    if curl --connect-timeout 10 --max-time 20 --fail --silent --show-error \
      --output "$body_file" "$endpoint"; then
      if [[ "$endpoint" != */actuator/health ]] || \
        grep -Eq '"status"[[:space:]]*:[[:space:]]*"UP"' "$body_file"; then
        break
      fi
    fi
    if [[ "$attempt" == 24 ]]; then
      echo "Healthcheck failed: $endpoint" >&2
      exit 1
    fi
    sleep 5
  done
done
