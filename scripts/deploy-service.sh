#!/usr/bin/env bash
set -euo pipefail
service="${1:?usage: deploy-service.sh <analytics|generator|web> <image> <sha>}"
image="${2:?image is required}"
sha="${3:?sha is required}"
case "$service" in analytics|generator|web) ;; *) echo 'Unsupported service.' >&2; exit 2;; esac
: "${FKIT_BI_DEV_HOST:?}" "${FKIT_BI_DEV_SSH_USER:?}" "${FKIT_BI_DEV_SSH_PORT:?}" "${FKIT_BI_DEV_DEPLOY_PATH:?}" "${FKIT_BI_DEV_SSH_KNOWN_HOSTS:?}" "${FKIT_BI_DEV_SSH_PRIVATE_KEY:?}"
case "$service" in
  web) health_url='http://localhost/' ;;
  analytics|generator) health_url='http://localhost:8080/actuator/health' ;;
esac
key="$(mktemp)"; known_hosts="$(mktemp)"
trap 'rm -f "$key" "$known_hosts"' EXIT
printf '%s\n' "$FKIT_BI_DEV_SSH_PRIVATE_KEY" > "$key"; chmod 600 "$key"
printf '%s\n' "$FKIT_BI_DEV_SSH_KNOWN_HOSTS" > "$known_hosts"
opts=(-i "$key" -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile="$known_hosts" -p "$FKIT_BI_DEV_SSH_PORT")
remote="$FKIT_BI_DEV_SSH_USER@$FKIT_BI_DEV_HOST"
# shellcheck disable=SC2029 # arguments deliberately expand locally; heredoc remains literal.
ssh "${opts[@]}" "$remote" "flock -w 300 /tmp/fkit-bi-deploy.lock bash -s -- '$service' '$image' '$sha' '$FKIT_BI_DEV_DEPLOY_PATH' '$health_url'" <<'REMOTE'
set -euo pipefail
service="$1"; image="$2"; sha="$3"; path="$4"; health_url="$5"
cd "$path"; test -f .env
key="$(tr '[:lower:]' '[:upper:]' <<< "$service")_IMAGE"
sed -i "s|^${key}=.*|${key}=${image}|;s|^GIT_SHA=.*|GIT_SHA=${sha}|" .env
docker compose pull "$service"
docker compose up -d --no-deps "$service"
for i in $(seq 1 24); do docker compose exec -T "$service" wget -qO- "$health_url" >/dev/null && exit 0; sleep 5; done
docker compose logs --tail=100 "$service" >&2; exit 1
REMOTE
