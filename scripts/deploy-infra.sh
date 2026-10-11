#!/usr/bin/env bash
# Applies an already-verified infra revision.  It never builds, pulls, or
# changes the image references in the server's private .env file.
set -euo pipefail

sha="${1:?usage: deploy-infra.sh <infra-git-sha>}"
case "$sha" in
  *[!0-9a-f]*|'') echo 'Infra SHA must be lowercase hexadecimal.' >&2; exit 2 ;;
esac

for setting in \
  FKIT_BI_DEV_HOST FKIT_BI_DEV_SSH_USER FKIT_BI_DEV_SSH_PORT \
  FKIT_BI_DEV_DEPLOY_PATH FKIT_BI_DEV_PUBLIC_URL \
  FKIT_BI_DEV_SSH_KNOWN_HOSTS FKIT_BI_DEV_SSH_PRIVATE_KEY \
  FKIT_BI_DEV_GRAFANA_ADMIN_PASSWORD; do
  if [[ -z "${!setting:-}" ]]; then
    echo "Required Dev setting is missing: $setting" >&2
    exit 2
  fi
done
if [[ ! "$FKIT_BI_DEV_GRAFANA_ADMIN_PASSWORD" =~ ^[0-9a-f]{64}$ ]]; then
  echo 'Dev Grafana admin secret must be 64 lowercase hexadecimal characters.' >&2
  exit 2
fi

case "$FKIT_BI_DEV_SSH_PORT" in
  *[!0-9]*|'') echo 'Dev SSH port must be numeric.' >&2; exit 2 ;;
esac
if [[ ! "$FKIT_BI_DEV_DEPLOY_PATH" =~ ^/[A-Za-z0-9._/-]+$ ]]; then
  echo 'Dev deploy path must be an absolute safe path.' >&2
  exit 2
fi

root="$(cd "$(dirname "$0")/.." && pwd)"
git -C "$root" cat-file -e "${sha}^{commit}"
resolved_sha="$(git -C "$root" rev-parse "${sha}^{commit}")"
[[ "$resolved_sha" == "$sha" ]] || { echo 'Infra SHA is not canonical.' >&2; exit 2; }
docker compose --project-directory "$root" --env-file "$root/.env.example" config --quiet
docker run --rm \
  --add-host analytics:127.0.0.1 --add-host generator:127.0.0.1 --add-host web:127.0.0.1 \
  -v "$root/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro" \
  nginx:1.27-alpine nginx -t

key="$(mktemp)"
known_hosts="$(mktemp)"
bundle="$(mktemp)"
grafana_password_file="$(mktemp)"
trap 'rm -f "$key" "$known_hosts" "$bundle" "$grafana_password_file"' EXIT
printf '%s\n' "$FKIT_BI_DEV_SSH_PRIVATE_KEY" > "$key"
chmod 600 "$key"
printf '%s\n' "$FKIT_BI_DEV_GRAFANA_ADMIN_PASSWORD" > "$grafana_password_file"
chmod 600 "$grafana_password_file"
printf '%s\n' "$FKIT_BI_DEV_SSH_KNOWN_HOSTS" > "$known_hosts"

git -C "$root" show-ref --verify --quiet refs/remotes/origin/develop || {
  echo 'Runner checkout is missing origin/develop history.' >&2
  exit 2
}
git -C "$root" bundle create "$bundle" refs/remotes/origin/develop "$sha"
git bundle verify "$bundle" >/dev/null 2>&1

ssh_opts=(
  -i "$key" -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=15
  -o ConnectionAttempts=1 -o ServerAliveInterval=15 -o ServerAliveCountMax=2
  -o "UserKnownHostsFile=$known_hosts" -p "$FKIT_BI_DEV_SSH_PORT"
)
remote="$FKIT_BI_DEV_SSH_USER@$FKIT_BI_DEV_HOST"
bundle_name="fkit-bi-infra-${sha}-${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}.bundle"
remote_bundle="/tmp/$bundle_name"
remote_password_file="/tmp/fkit-bi-grafana-${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}.secret"
scp_opts=(
  -p -i "$key" -o BatchMode=yes -o StrictHostKeyChecking=yes
  -o ConnectTimeout=15 -o ConnectionAttempts=1
  -o "UserKnownHostsFile=$known_hosts" -P "$FKIT_BI_DEV_SSH_PORT"
)
scp "${scp_opts[@]}" "$bundle" "$remote:$remote_bundle"
scp "${scp_opts[@]}" "$grafana_password_file" "$remote:$remote_password_file"

# The heredoc is literal: only positional arguments cross the trust boundary.
# shellcheck disable=SC2029
ssh "${ssh_opts[@]}" "$remote" \
  "flock -w 300 /tmp/fkit-bi-deploy.lock bash -s -- '$sha' '$FKIT_BI_DEV_DEPLOY_PATH' '$remote_bundle' '$remote_password_file'" <<'REMOTE'
set -euo pipefail
sha="$1"
path="$2"
bundle="$3"
password_file="$4"
preflight_dir=''
cleanup() {
  if [[ -n "$preflight_dir" ]]; then
    git -C "$path" worktree remove --force "$preflight_dir" >/dev/null 2>&1 || true
  fi
  rm -f "$bundle" "$password_file"
}
trap cleanup EXIT

cd "$path"
if [[ ! -f .env ]]; then
  echo 'Dev deployment is missing its private .env file.' >&2
  exit 1
fi
if [[ ! -f "$password_file" ]]; then
  echo 'Dev deployment is missing the temporary Grafana secret.' >&2
  exit 1
fi
grafana_bootstrap_password="$(<"$password_file")"
if [[ ! "$grafana_bootstrap_password" =~ ^[0-9a-f]{64}$ ]]; then
  echo 'Temporary Grafana secret has an invalid format.' >&2
  exit 1
fi
grafana_password="$(docker compose config --environment | sed -n 's/^GRAFANA_ADMIN_PASSWORD=//p' | tail -n 1)"
if [[ "$grafana_password" == \"*\" && "$grafana_password" == *\" ]]; then
  grafana_password="${grafana_password:1:${#grafana_password}-2}"
elif [[ "$grafana_password" == \'*\' && "$grafana_password" == *\' ]]; then
  grafana_password="${grafana_password:1:${#grafana_password}-2}"
fi
grafana_needs_reset=0
case "$grafana_password" in
  ''|replace-with-secret|replace-with-a-grafana-secret)
    env_tmp="$(mktemp .env.XXXXXX)"
    found_password=0
    while IFS= read -r line || [[ -n "$line" ]]; do
      if [[ "$line" == GRAFANA_ADMIN_PASSWORD=* ]]; then
        printf 'GRAFANA_ADMIN_PASSWORD=%s\n' "$grafana_bootstrap_password" >> "$env_tmp"
        found_password=1
      else
        printf '%s\n' "$line" >> "$env_tmp"
      fi
    done < .env
    if [[ "$found_password" == 0 ]]; then
      printf 'GRAFANA_ADMIN_PASSWORD=%s\n' "$grafana_bootstrap_password" >> "$env_tmp"
    fi
    chmod 600 "$env_tmp"
    mv -f "$env_tmp" .env
    grafana_needs_reset=1
    ;;
esac
if [[ -f .fkit-bi-grafana-bootstrap-pending ]]; then
  grafana_needs_reset=1
fi
if [[ "$grafana_needs_reset" == 1 ]]; then
  : > .fkit-bi-grafana-bootstrap-pending
  chmod 600 .fkit-bi-grafana-bootstrap-pending
fi
env_checksum_before="$(sha256sum .env)"

# The runner transfers a verified Git bundle so the Dev host needs no GitHub
# credentials. Initialize metadata beside existing runtime files on first use.
if [[ ! -d .git ]]; then
  git init -b develop . >/dev/null
fi
git fetch --no-tags "$bundle" \
  refs/remotes/origin/develop:refs/remotes/origin/develop
if ! git cat-file -e "${sha}^{commit}" 2>/dev/null; then
  echo 'Requested infra commit is not available on the Dev host.' >&2
  exit 1
fi
if ! git merge-base --is-ancestor "$sha" origin/develop; then
  echo 'Requested infra commit is not reachable from origin/develop.' >&2
  exit 1
fi
resolved_sha="$(git rev-parse "${sha}^{commit}")"
[[ "$resolved_sha" == "$sha" ]] || { echo 'Remote infra SHA cannot be resolved.' >&2; exit 1; }

preflight_dir="$(mktemp -d)"
git worktree add --detach "$preflight_dir" "$sha" >/dev/null
cp .env "$preflight_dir/.env"
docker compose --project-directory "$preflight_dir" --env-file "$preflight_dir/.env" config --quiet

git checkout --force --detach "$sha"
[[ "$(sha256sum .env)" == "$env_checksum_before" ]] || { echo '.env was unexpectedly changed.' >&2; exit 1; }
docker compose config --quiet

# Keep application image references unchanged. Build the pinned Certbot helper,
# then reconcile infrastructure and monitoring services; never recreate web.
docker compose build cert-setup
docker compose run --rm -T cert-setup </dev/null
docker compose up -d --no-build --pull never postgres analytics generator
docker compose up -d --no-build --pull never --no-recreate web
if ! docker image inspect nginx:1.27-alpine >/dev/null 2>&1; then
  docker compose pull proxy
fi
docker compose up -d --no-build --pull never --no-deps --force-recreate proxy
docker compose pull prometheus grafana postgres-exporter node-exporter
docker compose up -d --no-build --pull never prometheus grafana postgres-exporter node-exporter
if [[ "$grafana_needs_reset" == 1 ]]; then
  reset_ok=0
  for attempt in $(seq 1 12); do
    if docker compose exec -T grafana grafana cli admin reset-admin-password \
      "$grafana_bootstrap_password" </dev/null >/dev/null 2>&1; then
      reset_ok=1
      break
    fi
    sleep 5
  done
  if [[ "$reset_ok" != 1 ]]; then
    echo 'Grafana admin password reset failed; bootstrap will retry on the next delivery.' >&2
    exit 1
  fi
  rm -f .fkit-bi-grafana-bootstrap-pending
fi
docker compose up -d --no-build --pull never --no-deps cert-renew
printf '%s\n' "$sha" > .fkit-bi-infra-sha
docker compose ps
REMOTE

"$root/scripts/healthcheck.sh" "$FKIT_BI_DEV_PUBLIC_URL"
printf 'Infra delivery succeeded: %s\n' "$sha"
