#!/bin/bash
# Starts the Space (ADR-0023): a fresh PostgreSQL with the latest backup restored into it, the own
# model downloaded, the database brought up to date; then the API and nginx, and the jobs that keep
# it current: the collector (every 3 h) and the worker (own classifier and stories, every hour),
# each followed by a backup to the private dataset, which is what survives a restart.
#
# Needs the Space secret HF_TOKEN (read and write on DATA_REPO, read on MODEL_REPO). DUMP_FILE, if
# set, is restored instead of the dataset's (local tests); with no backup the site starts with the
# reference data only, and makes no backup unless FIRST_START=1.
set -euo pipefail

DATA_REPO=${DATA_REPO:-Juanan237/incontext-data}
DUMP_NAME=${DUMP_NAME:-live.dump}
MODEL_REPO=${MODEL_REPO:-Juanan237/incontext-model}
MODEL_NAME=${MODEL_NAME:-train-set-v5-paraphrase-multilingual-mpnet-base-v2-seed42}
export DATA_REPO DUMP_NAME
# The encoder baked into the image (HF_HOME=/opt/hf) is read-only; downloads and uploads use a
# cache of their own.
hub() { HF_HOME=/home/user/.hf HF_HUB_OFFLINE=0 python "$@"; }

event() { printf '{"event": "%s", "at": "%s"}\n' "$1" "$(date -u +%FT%TZ)"; }

# The Space disk is not persistent: every start begins with an empty cluster.
rm -rf "$PGDATA"
initdb --auth=trust --username=user --encoding=UTF8 --locale=C.UTF-8 "$PGDATA" >/dev/null
pg_ctl --wait --pgdata="$PGDATA" --log=/tmp/postgres.log \
  -o "-c listen_addresses=127.0.0.1 -c unix_socket_directories=/tmp" start
createdb --host=127.0.0.1 --username=user datos

dump=${DUMP_FILE:-}
if [[ -z "$dump" && -n "${HF_TOKEN:-}" ]]; then
  if dump=$(hub -c "from huggingface_hub import hf_hub_download as d
print(d('$DATA_REPO', '$DUMP_NAME', repo_type='dataset', local_dir='/tmp/restore'))"); then
    event backup_downloaded
  else
    event backup_not_downloaded
    dump=""
  fi
fi
restored=0
if [[ -n "$dump" ]]; then
  pg_restore --no-owner --exit-on-error --host=127.0.0.1 --username=user --dbname=datos "$dump"
  event backup_restored
  restored=1
fi
# A Space that did not restore its backup must never upload over it: an hour later the empty
# database would replace the real one. FIRST_START=1 allows it, for a dataset with no backup yet.
backing_up=0
if [[ -n "${HF_TOKEN:-}" && ( $restored == 1 || "${FIRST_START:-0}" == 1 ) ]]; then
  backing_up=1
elif [[ -n "${HF_TOKEN:-}" ]]; then
  event backups_off_nothing_restored
fi

# The same steps as docker/entrypoint.sh: migrations newer than the backup, then the CSV data of
# this commit.
alembic upgrade head
python -m datos.territories load
python -m datos.governments load
python -m datos.organization load

uvicorn datos.main:app --factory --host 127.0.0.1 --port 8000 &
nginx -c /etc/nginx/space.conf -g 'daemon off;' &
serving=$!

# The jobs need the token: without it the Space only serves what it restored.
if [[ -n "${HF_TOKEN:-}" ]]; then
  hub -c "from huggingface_hub import snapshot_download as d
d('$MODEL_REPO', allow_patterns='$MODEL_NAME/*', local_dir='$MODELS_DIR')" >/dev/null &&
    event model_downloaded || event model_not_downloaded
  # The data changes only when the collector or the worker store something: each backs up after
  # its cycle, so a restart loses at most a cycle in progress.
  if [[ $backing_up == 1 ]]; then
    export AFTER_CYCLE="HF_HOME=/home/user/.hf HF_HUB_OFFLINE=0 python /app/backup.py"
  fi
  collector.sh &
  HF_HUB_OFFLINE=1 MODEL_DIR="$MODELS_DIR/$MODEL_NAME" worker.sh &
else
  event jobs_not_started_no_token
fi

# On stop, one more backup if Hugging Face gives the time (on 2026-11-17 it did not: the cycles'
# backups are the ones that count).
stop() {
  event space_stopping
  if [[ $backing_up == 1 ]]; then
    HF_HOME=/home/user/.hf HF_HUB_OFFLINE=0 python /app/backup.py || event backup_on_stop_failed
  fi
  kill $(jobs -p) 2>/dev/null || true
  exit 0
}
trap stop TERM INT

# The Space lives while nginx does; if nginx stops, the container stops and is started again.
wait "$serving"
