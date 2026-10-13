#!/usr/bin/env bash
set -euo pipefail
infra_root="$(cd "$(dirname "$0")/.." && pwd)"
temporary_dir="$(mktemp -d)"
trap 'rm -r -- "$temporary_dir"' EXIT
export BOOTSTRAP_TEST_CAPTURE="$temporary_dir/docker-arguments"

cat > "$temporary_dir/docker" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' "$@" > "$BOOTSTRAP_TEST_CAPTURE"
STUB
chmod +x "$temporary_dir/docker"
export PATH="$temporary_dir:$PATH"

assert_docker_arguments() {
  local expected="$1"
  local actual
  actual="$(<"$BOOTSTRAP_TEST_CAPTURE")"
  if [[ "$actual" != "$expected" ]]; then
    printf 'Unexpected docker arguments:\n%s\n' "$actual" >&2
    return 1
  fi
}

export FKIT_BOOTSTRAP_USERNAME=probe.admin
export FKIT_BOOTSTRAP_DISPLAY_NAME='Проверочный оператор'
export FKIT_BOOTSTRAP_PASSWORD='not-a-real-secret-123'
output_file="$temporary_dir/wrapper-output"
"$infra_root/scripts/bootstrap-user.sh" >"$output_file" 2>&1
assert_docker_arguments "$(printf 'compose\nrun\n--rm\nanalytics-bootstrap')"
if grep -F -e "$FKIT_BOOTSTRAP_USERNAME" -e "$FKIT_BOOTSTRAP_DISPLAY_NAME" -e "$FKIT_BOOTSTRAP_PASSWORD" "$output_file"; then
  echo 'Bootstrap wrapper leaked credentials to output.' >&2
  exit 1
fi

: > "$BOOTSTRAP_TEST_CAPTURE"
"$infra_root/scripts/reset-bootstrap-password.sh" >"$output_file" 2>&1
assert_docker_arguments "$(printf 'compose\nrun\n--rm\nanalytics-bootstrap\nreset-bootstrap-password')"
docker_arguments="$(<"$BOOTSTRAP_TEST_CAPTURE")"
if [[ "$docker_arguments" == *"$FKIT_BOOTSTRAP_PASSWORD"* ]]; then
  echo 'Bootstrap password leaked into docker arguments.' >&2
  exit 1
fi
if grep -F -e "$FKIT_BOOTSTRAP_USERNAME" -e "$FKIT_BOOTSTRAP_DISPLAY_NAME" -e "$FKIT_BOOTSTRAP_PASSWORD" "$output_file"; then
  echo 'Reset wrapper leaked credentials to output.' >&2
  exit 1
fi

check_missing_variable() {
  local script="$1" missing="$2"
  : > "$BOOTSTRAP_TEST_CAPTURE"
  if env -u "$missing" "$infra_root/scripts/$script" >"$output_file" 2>&1; then
    printf '%s accepted missing %s.\n' "$script" "$missing" >&2
    return 1
  fi
  if [[ -s "$BOOTSTRAP_TEST_CAPTURE" ]]; then
    printf 'Docker ran without %s for %s.\n' "$missing" "$script" >&2
    return 1
  fi
}

check_missing_variable bootstrap-user.sh FKIT_BOOTSTRAP_USERNAME
check_missing_variable bootstrap-user.sh FKIT_BOOTSTRAP_DISPLAY_NAME
check_missing_variable bootstrap-user.sh FKIT_BOOTSTRAP_PASSWORD
check_missing_variable reset-bootstrap-password.sh FKIT_BOOTSTRAP_USERNAME
check_missing_variable reset-bootstrap-password.sh FKIT_BOOTSTRAP_PASSWORD

echo 'Bootstrap command wrappers passed.'
