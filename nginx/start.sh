#!/bin/sh
# shellcheck disable=SC2016 # envsubst receives a literal variable allow-list.
set -eu

case "${TLS_MODE:-off}" in
  off)
    rm -f /etc/nginx/conf.d/tls.conf
    ;;
  self-signed)
    TLS_CERT_DIR=/etc/letsencrypt/self-signed/bi.kitexp.ru
    [ -s "$TLS_CERT_DIR/fullchain.pem" ] && [ -s "$TLS_CERT_DIR/privkey.pem" ] || {
      echo 'Self-signed TLS certificate is missing.' >&2
      exit 1
    }
    export TLS_CERT_DIR
    envsubst '$TLS_CERT_DIR' < /etc/nginx/tls.conf.template > /etc/nginx/conf.d/tls.conf
    ;;
  public)
    TLS_CERT_DIR=/etc/letsencrypt/live/bi.kitexp.ru
    [ -s "$TLS_CERT_DIR/fullchain.pem" ] && [ -s "$TLS_CERT_DIR/privkey.pem" ] || {
      echo 'Public TLS certificate is missing.' >&2
      exit 1
    }
    export TLS_CERT_DIR
    envsubst '$TLS_CERT_DIR' < /etc/nginx/tls.conf.template > /etc/nginx/conf.d/tls.conf
    ;;
  *)
    echo "Unsupported TLS_MODE: ${TLS_MODE}" >&2
    exit 2
    ;;
esac

exec nginx -g 'daemon off;'
