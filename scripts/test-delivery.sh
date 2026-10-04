#!/usr/bin/env bash
# Локальные проверки защитных контрактов delivery без SSH, Docker image pull
# или обращения к Dev.
set -euo pipefail
cd "$(dirname "$0")/.."

temporary_dir="$(mktemp -d)"
trap 'rm -rf "$temporary_dir"' EXIT
mkdir -p "$temporary_dir/bin"

cat > "$temporary_dir/bin/ssh" <<'EOF'
#!/usr/bin/env bash
echo 'ssh must not be called during preflight failure' >&2
exit 99
EOF
chmod +x "$temporary_dir/bin/ssh"

expect_failure() {
  local expected="$1"
  shift
  local output status
  set +e
  output="$("$@" 2>&1)"
  status=$?
  set -e
  [[ $status -ne 0 ]] || { echo "Expected failure: $*" >&2; exit 1; }
  [[ "$output" == *"$expected"* ]] || {
    echo "Expected diagnostic not found: $expected" >&2
    echo "$output" >&2
    exit 1
  }
}

# Неполные settings и неверный SHA останавливаются до SSH.
expect_failure 'Required Dev setting is missing: FKIT_BI_DEV_HOST' \
  env PATH="$temporary_dir/bin:$PATH" ./scripts/deploy-infra.sh \
  f5f0e7b6519a01233ab503f88e078cd7e239bc00
expect_failure 'Infra SHA must be lowercase hexadecimal.' \
  env PATH="$temporary_dir/bin:$PATH" ./scripts/deploy-infra.sh not-a-sha
expect_failure 'Dev deploy path must be an absolute safe path.' env \
  PATH="$temporary_dir/bin:$PATH" \
  FKIT_BI_DEV_HOST=dev.example.test \
  FKIT_BI_DEV_SSH_USER=deployer \
  FKIT_BI_DEV_SSH_PORT=22 \
  "FKIT_BI_DEV_DEPLOY_PATH=/opt/fkit-bi' injected" \
  FKIT_BI_DEV_PUBLIC_URL=http://dev.example.test \
  FKIT_BI_DEV_SSH_KNOWN_HOSTS='dev.example.test ssh-ed25519 AAAA' \
  FKIT_BI_DEV_SSH_PRIVATE_KEY='test private key' \
  ./scripts/deploy-infra.sh f5f0e7b6519a01233ab503f88e078cd7e239bc00

# Внешний контракт healthcheck включает public URL и оба API.
health_log="$temporary_dir/health.log"
cat > "$temporary_dir/bin/curl" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "${!#}" >> "$FKIT_BI_TEST_HEALTH_LOG"
EOF
chmod +x "$temporary_dir/bin/curl"
FKIT_BI_TEST_HEALTH_LOG="$health_log" PATH="$temporary_dir/bin:$PATH" \
  ./scripts/healthcheck.sh http://dev.example.test
grep -Fx 'http://dev.example.test/' "$health_log" >/dev/null
grep -Fx 'http://dev.example.test/api/analytics/actuator/health' "$health_log" >/dev/null
grep -Fx 'http://dev.example.test/api/generator/actuator/health' "$health_log" >/dev/null

# CI не доставляет из PR и сообщает выключенное состояние в summary.
grep -F "if: github.event_name == 'push' && github.ref == 'refs/heads/develop'" \
  .github/workflows/ci.yml >/dev/null
grep -F "Dev infra delivery is disabled" .github/workflows/ci.yml >/dev/null

# A successful delivery is executed entirely through stubs.  This exercises
# the remote heredoc and proves its exact-SHA, private-.env and no-pull/web
# recreation contract without connecting to Dev.
test_sha='f5f0e7b6519a01233ab503f88e078cd7e239bc00'
server_dir="$temporary_dir/server"
mkdir -p "$server_dir/.git"
printf '%s\n' 'PRIVATE_VALUE=unchanged' > "$server_dir/.env"
env_before="$(sha256sum "$server_dir/.env")"
delivery_log="$temporary_dir/delivery.log"

cat > "$temporary_dir/bin/git" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'git %s\n' "$*" >> "$FKIT_BI_TEST_DELIVERY_LOG"
if [[ "${1:-}" == '-C' ]]; then shift 2; fi
case "${1:-}" in
  rev-parse) printf '%s\n' "$FKIT_BI_TEST_SHA" ;;
  worktree)
    if [[ "${2:-}" == add ]]; then mkdir -p "${4:?}/nginx"; fi
    ;;
esac
EOF
cat > "$temporary_dir/bin/docker" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\n' "$*" >> "$FKIT_BI_TEST_DELIVERY_LOG"
EOF
cat > "$temporary_dir/bin/ssh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'ssh %s\n' "$*" >> "$FKIT_BI_TEST_DELIVERY_LOG"
# Arguments are validated by deploy-infra.sh; execute the literal remote body
# with the test's known safe values rather than parsing a shell command string.
bash -s -- "$FKIT_BI_TEST_SHA" "$FKIT_BI_TEST_SERVER_DIR"
EOF
cat > "$temporary_dir/bin/curl" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$temporary_dir/bin/git" "$temporary_dir/bin/docker" \
  "$temporary_dir/bin/ssh" "$temporary_dir/bin/curl"

env \
  PATH="$temporary_dir/bin:$PATH" \
  FKIT_BI_TEST_SHA="$test_sha" \
  FKIT_BI_TEST_SERVER_DIR="$server_dir" \
  FKIT_BI_TEST_DELIVERY_LOG="$delivery_log" \
  FKIT_BI_DEV_HOST=dev.example.test \
  FKIT_BI_DEV_SSH_USER=deployer \
  FKIT_BI_DEV_SSH_PORT=22 \
  FKIT_BI_DEV_DEPLOY_PATH="$server_dir" \
  FKIT_BI_DEV_PUBLIC_URL=http://dev.example.test \
  FKIT_BI_DEV_SSH_KNOWN_HOSTS='dev.example.test ssh-ed25519 AAAA' \
  FKIT_BI_DEV_SSH_PRIVATE_KEY='test private key' \
  ./scripts/deploy-infra.sh "$test_sha" >/dev/null

[[ "$(sha256sum "$server_dir/.env")" == "$env_before" ]]
grep -F "git checkout --detach $test_sha" "$delivery_log" >/dev/null
grep -F 'docker run --rm --pull never' "$delivery_log" >/dev/null
grep -F 'nginx:1.27-alpine nginx -t' "$delivery_log" >/dev/null
grep -F 'docker compose up -d --no-build --pull never --no-recreate web' "$delivery_log" >/dev/null
grep -F 'docker compose up -d --no-build --pull never --no-deps --force-recreate proxy' "$delivery_log" >/dev/null
if grep -F 'docker compose pull' "$delivery_log" >/dev/null; then
  echo 'Infra delivery must not pull images.' >&2
  exit 1
fi

# bootstrap-dev starts the complete currently-published service set.
bootstrap_dir="$temporary_dir/bootstrap"
mkdir -p "$bootstrap_dir/scripts"
cp scripts/bootstrap-dev.sh scripts/healthcheck.sh "$bootstrap_dir/scripts/"
cp .env.example "$bootstrap_dir/.env"
: > "$delivery_log"
FKIT_BI_TEST_DELIVERY_LOG="$delivery_log" FKIT_BI_DEV_PUBLIC_URL=http://dev.example.test \
  PATH="$temporary_dir/bin:$PATH" "$bootstrap_dir/scripts/bootstrap-dev.sh"
grep -F 'docker compose up -d --no-build postgres analytics generator web proxy' "$delivery_log" >/dev/null

# Healthchecks retry deterministically and report a failure after the bounded
# attempt count without waiting in the test.
health_count="$temporary_dir/health-count"
sleep_count="$temporary_dir/sleep-count"
cat > "$temporary_dir/bin/curl" <<'EOF'
#!/usr/bin/env bash
count=0
[[ -f "$FKIT_BI_TEST_HEALTH_COUNT" ]] && count="$(<"$FKIT_BI_TEST_HEALTH_COUNT")"
count=$((count + 1))
printf '%s\n' "$count" > "$FKIT_BI_TEST_HEALTH_COUNT"
[[ "${FKIT_BI_TEST_HEALTH_MODE:-}" == fail ]] && exit 1
(( count > 2 ))
EOF
cat > "$temporary_dir/bin/sleep" <<'EOF'
#!/usr/bin/env bash
count=0
[[ -f "$FKIT_BI_TEST_SLEEP_COUNT" ]] && count="$(<"$FKIT_BI_TEST_SLEEP_COUNT")"
printf '%s\n' "$((count + 1))" > "$FKIT_BI_TEST_SLEEP_COUNT"
EOF
chmod +x "$temporary_dir/bin/curl" "$temporary_dir/bin/sleep"
FKIT_BI_TEST_HEALTH_COUNT="$health_count" FKIT_BI_TEST_SLEEP_COUNT="$sleep_count" \
  PATH="$temporary_dir/bin:$PATH" ./scripts/healthcheck.sh http://dev.example.test
[[ "$(<"$health_count")" == 5 ]]
[[ "$(<"$sleep_count")" == 2 ]]

: > "$health_count"
: > "$sleep_count"
expect_failure 'Healthcheck failed: http://dev.example.test/' env \
  FKIT_BI_TEST_HEALTH_MODE=fail \
  FKIT_BI_TEST_HEALTH_COUNT="$health_count" \
  FKIT_BI_TEST_SLEEP_COUNT="$sleep_count" \
  PATH="$temporary_dir/bin:$PATH" ./scripts/healthcheck.sh http://dev.example.test
[[ "$(<"$health_count")" == 24 ]]
[[ "$(<"$sleep_count")" == 23 ]]
