#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose --env-file .env.example config --quiet
for tls_mode in off self-signed public; do
  TLS_MODE="$tls_mode" docker compose --env-file .env.example config --quiet
done
python3 scripts/test-runtime-contracts.py
python3 scripts/test-edge-http.py
python3 certbot/test_renew.py
python3 certbot/test_setup.py
./scripts/test-delivery.sh

# Exercise the actual Compose Certbot entrypoint in the no-TLS local mode.
certbot_contract_project="fkit-cert-setup-contract-$$"
if ! docker compose --project-name "$certbot_contract_project" --env-file .env.example \
  run --rm --no-deps cert-setup; then
  docker compose --project-name "$certbot_contract_project" down --volumes --remove-orphans
  exit 1
fi
docker compose --project-name "$certbot_contract_project" down --volumes --remove-orphans

# Validate both the always-on HTTP config and the optional TLS listener with
# disposable files. No Compose stack, DNS credentials, ACME request or deploy.
docker run --rm \
  --add-host analytics:127.0.0.1 --add-host generator:127.0.0.1 \
  -v "$PWD/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro" \
  nginx:1.27-alpine nginx -t
tls_validation_dir=$(mktemp -d "$PWD/.tls-validate.XXXXXX")
trap 'rm -r -- "$tls_validation_dir"' EXIT
mkdir -p "$tls_validation_dir/live/bi.kitexp.ru"
sed "s|\${TLS_CERT_DIR}|/etc/letsencrypt/live/bi.kitexp.ru|g" \
  nginx/tls.conf.template > "$tls_validation_dir/tls.conf"
openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
  -keyout "$tls_validation_dir/live/bi.kitexp.ru/privkey.pem" \
  -out "$tls_validation_dir/live/bi.kitexp.ru/fullchain.pem" \
  -subj '/CN=bi.kitexp.ru' \
  -addext 'subjectAltName=DNS:bi.kitexp.ru,DNS:*.bi.kitexp.ru' \
  >/dev/null 2>&1
docker run --rm \
  --add-host analytics:127.0.0.1 --add-host generator:127.0.0.1 \
  -v "$PWD/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro" \
  -v "$tls_validation_dir/tls.conf:/etc/nginx/conf.d/tls.conf:ro" \
  -v "$tls_validation_dir:/etc/letsencrypt:ro" \
  nginx:1.27-alpine nginx -t

# Yandex DNS auth/cleanup behavior is exercised with a mocked API, never live.
docker compose --env-file .env.example build cert-setup
docker run --rm -v "$PWD/certbot:/work:ro" -w /work \
  --entrypoint python3 fkit-bi-certbot:local -m unittest test_yandex_dns.py
docker run --rm --tmpfs /etc/letsencrypt:rw \
  -v "$PWD/certbot:/opt/fkit/certbot:ro" \
  --entrypoint /bin/sh fkit-bi-certbot:local -c '
    set -eu
    TLS_MODE=off sh /opt/fkit/certbot/setup.sh
    test ! -s /etc/letsencrypt/self-signed/bi.kitexp.ru/fullchain.pem
    TLS_MODE=self-signed sh /opt/fkit/certbot/setup.sh
    before="$(openssl x509 -in /etc/letsencrypt/self-signed/bi.kitexp.ru/fullchain.pem -noout -fingerprint)"
    TLS_MODE=self-signed sh /opt/fkit/certbot/setup.sh
    after="$(openssl x509 -in /etc/letsencrypt/self-signed/bi.kitexp.ru/fullchain.pem -noout -fingerprint)"
    test "$before" = "$after"
    cert_dir=/etc/letsencrypt/self-signed/bi.kitexp.ru
    printf corrupt > "$cert_dir/fullchain.pem"
    TLS_MODE=self-signed sh /opt/fkit/certbot/setup.sh
    cert_hash="$(openssl x509 -in "$cert_dir/fullchain.pem" -pubkey -noout | openssl pkey -pubin -outform der | openssl sha256)"
    key_hash="$(openssl pkey -in "$cert_dir/privkey.pem" -pubout -outform der | openssl sha256)"
    test "$cert_hash" = "$key_hash"
    if TLS_MODE=public sh /opt/fkit/certbot/setup.sh; then
      echo "Public TLS without external settings must fail." >&2
      exit 1
    fi
    openssl x509 -in "$cert_dir/fullchain.pem" -noout >/dev/null
  '

# Validate scrape configuration, rules and firing behavior using Prometheus's
# pinned promtool image.
docker run --rm -v "$PWD/observability/prometheus:/etc/prometheus:ro" \
  --entrypoint /bin/promtool prom/prometheus:v3.5.0 \
  check config /etc/prometheus/prometheus.yml
docker run --rm -v "$PWD/observability/prometheus:/etc/prometheus:ro" \
  --entrypoint /bin/promtool prom/prometheus:v3.5.0 \
  check rules /etc/prometheus/rules/fkit-bi-alerts.yml
docker run --rm -w /etc/prometheus/tests \
  -v "$PWD/observability/prometheus:/etc/prometheus:ro" \
  --entrypoint /bin/promtool prom/prometheus:v3.5.0 \
  test rules fkit-bi-alerts.test.yml
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

# Build test-tagged application images and exercise runtime independence in a
# unique Compose project. The test always removes that project's volumes.
python3 scripts/test-monitoring-isolation.py
