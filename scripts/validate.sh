#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose --env-file .env.example config --quiet
./scripts/test-delivery.sh
if command -v shellcheck >/dev/null 2>&1; then
  shellcheck scripts/*.sh
else
  docker run --rm -v "$PWD:/repo:ro" -w /repo koalaman/shellcheck:v0.10.0 \
    scripts/*.sh
fi

# actionlint validates GitHub Actions expressions and workflow semantics, not
# just YAML syntax.  The container tag is deliberately pinned for CI parity.
if command -v actionlint >/dev/null 2>&1; then
  actionlint .github/workflows/*.yml
else
  docker run --rm -v "$PWD:/repo:ro" -w /repo rhysd/actionlint:1.7.7 \
    -color .github/workflows/*.yml
fi
