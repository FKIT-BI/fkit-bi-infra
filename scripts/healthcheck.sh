#!/usr/bin/env bash
set -euo pipefail
url="${1:?usage: healthcheck.sh <public-url>}"
curl --fail --silent --show-error "$url/"
curl --fail --silent --show-error "$url/api/analytics/actuator/health"
curl --fail --silent --show-error "$url/api/generator/actuator/health"
