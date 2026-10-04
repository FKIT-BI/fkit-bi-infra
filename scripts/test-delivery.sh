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

# Service delivery chooses the health endpoint for the selected runtime.
cat > "$temporary_dir/bin/flock" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
shift 3
exec "$@"
EOF
cat > "$temporary_dir/bin/docker" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\n' "$*" >> "$FKIT_BI_TEST_SERVICE_LOG"
EOF
cat > "$temporary_dir/bin/ssh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
remote_command="${!#}"
bash -c "$remote_command"
EOF
chmod +x "$temporary_dir/bin/flock" "$temporary_dir/bin/docker" "$temporary_dir/bin/ssh"

run_service_delivery() {
  local service="$1" expected_health="$2"
  local deployment_dir="$temporary_dir/service-$service"
  local service_log="$temporary_dir/service-$service.log"
  mkdir -p "$deployment_dir"
  printf '%s\n' \
    'ANALYTICS_IMAGE=old-analytics' \
    'GENERATOR_IMAGE=old-generator' \
    'WEB_IMAGE=old-web' \
    'GIT_SHA=old-sha' > "$deployment_dir/.env"
  FKIT_BI_TEST_SERVICE_LOG="$service_log" \
    FKIT_BI_DEV_HOST=dev.example.test \
    FKIT_BI_DEV_SSH_USER=deployer \
    FKIT_BI_DEV_SSH_PORT=22 \
    FKIT_BI_DEV_DEPLOY_PATH="$deployment_dir" \
    FKIT_BI_DEV_SSH_KNOWN_HOSTS='dev.example.test ssh-ed25519 AAAA' \
    FKIT_BI_DEV_SSH_PRIVATE_KEY='test private key' \
    PATH="$temporary_dir/bin:$PATH" \
  ./scripts/deploy-service.sh "$service" "image-$service" test-sha >/dev/null
  grep -F "wget -qO- $expected_health" "$service_log" >/dev/null
  grep -Fx "GIT_SHA=test-sha" "$deployment_dir/.env" >/dev/null
  grep -Fx "$(tr '[:lower:]' '[:upper:]' <<< "$service")_IMAGE=image-$service" "$deployment_dir/.env" >/dev/null
  if [[ "$service" != web ]]; then
    grep -Fx 'WEB_IMAGE=old-web' "$deployment_dir/.env" >/dev/null
  fi
  if [[ "$service" != analytics ]]; then
    grep -Fx 'ANALYTICS_IMAGE=old-analytics' "$deployment_dir/.env" >/dev/null
  fi
  if [[ "$service" != generator ]]; then
    grep -Fx 'GENERATOR_IMAGE=old-generator' "$deployment_dir/.env" >/dev/null
  fi
}

run_service_delivery analytics 'http://localhost:8080/actuator/health'
run_service_delivery generator 'http://localhost:8080/actuator/health'
run_service_delivery web 'http://localhost/'

# Invalid service names are rejected before SSH is invoked.
expect_failure 'Unsupported service.' env \
  FKIT_BI_DEV_HOST=dev.example.test \
  FKIT_BI_DEV_SSH_USER=deployer \
  FKIT_BI_DEV_SSH_PORT=22 \
  FKIT_BI_DEV_DEPLOY_PATH="$temporary_dir/service-invalid" \
  FKIT_BI_DEV_SSH_KNOWN_HOSTS='dev.example.test ssh-ed25519 AAAA' \
  FKIT_BI_DEV_SSH_PRIVATE_KEY='test private key' \
  PATH="$temporary_dir/bin:$PATH" \
  ./scripts/deploy-service.sh invalid image sha

# CI не доставляет из PR и сообщает выключенное состояние в summary.
grep -F "if: github.event_name == 'push' && github.ref == 'refs/heads/develop'" \
  .github/workflows/ci.yml >/dev/null
grep -F "Dev infra delivery is disabled" .github/workflows/ci.yml >/dev/null

# A successful delivery is executed entirely through stubs.  This exercises
# the remote heredoc and proves its exact-SHA, private-.env and no-pull/web
# recreation contract without connecting to Dev.
test_sha="$(git rev-parse refs/remotes/origin/develop)"
server_dir="$temporary_dir/server"
mkdir -p "$server_dir"
printf '%s\n' 'PRIVATE_VALUE=unchanged' > "$server_dir/.env"
env_before="$(sha256sum "$server_dir/.env")"
delivery_log="$temporary_dir/delivery.log"

cat > "$temporary_dir/bin/docker" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\n' "$*" >> "$FKIT_BI_TEST_DELIVERY_LOG"
EOF
cat > "$temporary_dir/bin/scp" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
remote_target="${!#}"
remote_path="${remote_target#*:}"
source_file="${@: -2:1}"
cp "$source_file" "$remote_path"
EOF
cat > "$temporary_dir/bin/ssh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'ssh %s\n' "$*" >> "$FKIT_BI_TEST_DELIVERY_LOG"
# Arguments are validated by deploy-infra.sh; execute the literal remote body
# with the test's known safe values rather than parsing a shell command string.
remote_command="${!#}"
bash -c "$remote_command"
EOF
cat > "$temporary_dir/bin/curl" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$temporary_dir/bin/scp" "$temporary_dir/bin/docker" \
  "$temporary_dir/bin/ssh" "$temporary_dir/bin/curl"

env \
  PATH="$temporary_dir/bin:$PATH" \
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
[[ "$(git -C "$server_dir" rev-parse HEAD)" == "$test_sha" ]]
grep -Fx "$test_sha" "$server_dir/.fkit-bi-infra-sha" >/dev/null
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
