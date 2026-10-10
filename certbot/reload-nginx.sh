#!/bin/sh
set -eu
kill -HUP "${NGINX_MASTER_PID:-1}"
