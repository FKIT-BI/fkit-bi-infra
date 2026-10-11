#!/bin/sh
set -eu

mode="${TLS_MODE:-off}"
challenge="${CERTBOT_CHALLENGE:-dns-01}"
webroot="${CERTBOT_WEBROOT:-/var/www/certbot}"
self_signed_dir=/etc/letsencrypt/self-signed/bi.kitexp.ru
public_live_dir=/etc/letsencrypt/live/bi.kitexp.ru

valid_certificate_pair() {
  cert="$1/fullchain.pem"
  key="$1/privkey.pem"
  [ -s "$cert" ] && [ -s "$key" ] || return 1
  openssl x509 -in "$cert" -noout >/dev/null 2>&1 || return 1
  openssl x509 -in "$cert" -checkend 86400 -noout >/dev/null 2>&1 || return 1
  openssl pkey -in "$key" -noout >/dev/null 2>&1
}

certificate_key_match() {
  cert="$1/fullchain.pem"
  key="$1/privkey.pem"
  cert_hash="$(openssl x509 -in "$cert" -pubkey -noout 2>/dev/null | openssl pkey -pubin -outform der 2>/dev/null | openssl sha256)" || return 1
  key_hash="$(openssl pkey -in "$key" -pubout -outform der 2>/dev/null | openssl sha256)" || return 1
  [ "$cert_hash" = "$key_hash" ]
}
case "$mode" in
  off)
    echo "TLS_MODE=off; Certbot is not started."
    exit 0
    ;;
  self-signed)
    cert_dir="$self_signed_dir"
    mkdir -p "$cert_dir"
    if ! valid_certificate_pair "$cert_dir" || ! certificate_key_match "$cert_dir" \
      || ! openssl x509 -in "$cert_dir/fullchain.pem" -checkhost bi.kitexp.ru -noout >/dev/null 2>&1 \
      || ! openssl x509 -in "$cert_dir/fullchain.pem" -checkhost node.bi.kitexp.ru -noout >/dev/null 2>&1; then
      cert_tmp="$cert_dir/fullchain.pem.tmp"
      key_tmp="$cert_dir/privkey.pem.tmp"
      openssl req -x509 -nodes -newkey rsa:2048 -days 3650 \
        -keyout "$key_tmp" \
        -out "$cert_tmp" \
        -subj '/CN=bi.kitexp.ru' \
        -addext 'subjectAltName=DNS:bi.kitexp.ru,DNS:*.bi.kitexp.ru'
      chmod 600 "$key_tmp"
      mv "$key_tmp" "$cert_dir/privkey.pem"
      mv "$cert_tmp" "$cert_dir/fullchain.pem"
    fi
    echo 'Persistent self-signed certificate is ready.'
    ;;
  public)
    : "${CERTBOT_EMAIL:?CERTBOT_EMAIL is required for TLS_MODE=public}"
    if [ -d "$public_live_dir" ] && [ ! -s /etc/letsencrypt/renewal/bi.kitexp.ru.conf ]; then
      legacy_dir="/etc/letsencrypt/self-signed/legacy-bi.kitexp.ru-$(date +%s)"
      mkdir -p /etc/letsencrypt/self-signed
      # Preserve the currently served material as regular files before moving
      # Certbot's relative symlinks; the archived lineage itself stays intact.
      if [ -s "$public_live_dir/fullchain.pem" ] && [ -s "$public_live_dir/privkey.pem" ]; then
        cp -L "$public_live_dir/fullchain.pem" "$legacy_dir.fullchain.pem"
        cp -L "$public_live_dir/privkey.pem" "$legacy_dir.privkey.pem"
        chmod 600 "$legacy_dir.privkey.pem"
      fi
      mv "$public_live_dir" "$legacy_dir"
      echo "Saved the unmanaged legacy certificate and key at $legacy_dir.fullchain.pem and $legacy_dir.privkey.pem."
    fi
    case "$challenge" in
      http-01)
        mkdir -p "$webroot/.well-known/acme-challenge"
        certbot certonly --non-interactive --agree-tos --email "$CERTBOT_EMAIL" \
          --webroot --webroot-path "$webroot" --preferred-challenges http \
          --cert-name bi.kitexp.ru \
          -d bi.kitexp.ru -d api.bi.kitexp.ru -d generator.bi.kitexp.ru
        ;;
      dns-01)
        : "${DNS_ZONE_ID:?DNS_ZONE_ID is required for public DNS-01}"
        : "${YANDEX_SERVICE_ACCOUNT_ID:?YANDEX_SERVICE_ACCOUNT_ID is required for public DNS-01}"
        : "${YANDEX_KEY_ID:?YANDEX_KEY_ID is required for public DNS-01}"
        key_file="${YANDEX_SERVICE_ACCOUNT_KEY_FILE:-/run/secrets/yandex-service-account-key.json}"
        test -s "$key_file" || {
          echo 'Yandex service-account key file is missing.' >&2
          exit 1
        }
        python3 /opt/fkit/certbot/yandex_dns.py validate
        certbot certonly --non-interactive --agree-tos --email "$CERTBOT_EMAIL" \
          --manual --preferred-challenges dns \
          --manual-auth-hook 'python3 /opt/fkit/certbot/yandex_dns.py auth' \
          --manual-cleanup-hook 'python3 /opt/fkit/certbot/yandex_dns.py cleanup' \
          --cert-name bi.kitexp.ru -d bi.kitexp.ru -d '*.bi.kitexp.ru'
        ;;
      *)
        echo "Unsupported CERTBOT_CHALLENGE: $challenge" >&2
        exit 2
        ;;
    esac
    ;;
  *)
    echo "Unsupported TLS_MODE: $mode" >&2
    exit 2
    ;;
esac
