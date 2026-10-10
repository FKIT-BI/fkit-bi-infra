#!/bin/sh
set -u
reload_hook="${RELOAD_HOOK:-/opt/fkit/certbot/reload-nginx.sh}"
if [ "${TLS_MODE:-off}" != public ]; then
  exec sleep infinity
fi
while :; do
  if certbot renew --non-interactive --deploy-hook "$reload_hook"; then
    echo 'Certbot renewal check completed.'
  else
    echo 'Certbot renewal failed; the current certificate is retained.' >&2
  fi
  sleep 12h
done
