#!/bin/sh
# Starts the Space (ADR-0023): a fresh PostgreSQL, the latest snapshot restored into it, the
# database brought up to date, then the API and nginx.
#
# The snapshot comes from the private dataset DATA_REPO (default Juanan237/incontext-data), read
# with the Space secret HF_TOKEN. SNAPSHOT_FILE, if set, is restored instead (local tests). With no
# snapshot the site starts with the reference data only (territories, governments) and says so.
set -eu

DATA_REPO=${DATA_REPO:-Juanan237/incontext-data}
snapshot=${SNAPSHOT_FILE:-/tmp/datos.dump}

# The Space disk is not persistent: every start begins with an empty cluster.
rm -rf "$PGDATA"
initdb --auth=trust --username=user --encoding=UTF8 --locale=C.UTF-8 "$PGDATA" >/dev/null
pg_ctl --wait --pgdata="$PGDATA" --log=/tmp/postgres.log \
  -o "-c listen_addresses=127.0.0.1 -c unix_socket_directories=/tmp" start
createdb --host=127.0.0.1 --username=user datos

if [ -z "${SNAPSHOT_FILE:-}" ]; then
  if [ -n "${HF_TOKEN:-}" ] && curl -fsSL -H "Authorization: Bearer $HF_TOKEN" \
    -o "$snapshot" "https://huggingface.co/datasets/$DATA_REPO/resolve/main/datos.dump"; then
    echo '{"event": "snapshot_downloaded"}'
  else
    echo '{"event": "snapshot_not_downloaded", "reason": "no HF_TOKEN or the download failed"}'
    snapshot=""
  fi
fi
if [ -n "$snapshot" ]; then
  pg_restore --no-owner --exit-on-error --host=127.0.0.1 --username=user --dbname=datos "$snapshot"
  echo '{"event": "snapshot_restored"}'
fi

# The same steps as docker/entrypoint.sh: migrations newer than the snapshot, then the CSV data
# of this commit (so a deploy with new sectors or governments shows them before the next snapshot).
alembic upgrade head
python -m datos.territories load
python -m datos.governments load

uvicorn datos.main:app --factory --host 127.0.0.1 --port 8000 &
exec nginx -c /etc/nginx/space.conf -g 'daemon off;'
