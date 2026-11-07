#!/bin/sh
# Volumes montados chegam como root: acerta o dono e roda o app sem privilégios.
set -e
if [ "$(id -u)" = "0" ]; then
  mkdir -p /data && chown -R app:app /data
  exec setpriv --reuid=app --regid=app --init-groups "$@"
fi
exec "$@"
