#!/usr/bin/env bash
# Publishes the daily snapshot the Hugging Face Space starts from (ADR-0023): a dump of the local
# database with every lead removed and no embeddings, uploaded to a private dataset; then the Space
# is restarted so it loads it. Meant for a scheduler (scripts/launchd/es.datos.publish-snapshot.plist).
#
#   scripts/publish-snapshot.sh              # dump, upload, restart the Space
#   scripts/publish-snapshot.sh --no-upload  # only write var/snapshot/datos.dump (to test it)
#
# Uploading needs a Hugging Face login with write access on this machine, once: `hf auth login`.
# DATA_REPO and SPACE_REPO change the targets (defaults below).
set -euo pipefail

cd "$(dirname "$0")/.."
export PATH="$HOME/.docker/bin:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

DATA_REPO=${DATA_REPO:-Juanan237/incontext-data}
SPACE_REPO=${SPACE_REPO:-Juanan237/incontext}
out=var/snapshot/datos.dump
mkdir -p var/snapshot

psql_in_db() { docker compose exec -T db psql -U datos -v ON_ERROR_STOP=1 -q "$@"; }

docker compose up -d --wait db >/dev/null

# The lead is processed here and never published (project policies), so the copy is cleaned in a
# scratch database before it is dumped. Embeddings are left out: the API does not read them.
psql_in_db -d postgres -c "DROP DATABASE IF EXISTS snapshot" -c "CREATE DATABASE snapshot"
docker compose exec -T db sh -c \
  "pg_dump -U datos -d datos -Fc --no-owner --no-privileges --exclude-table-data=article_embeddings \
   | pg_restore -U datos -d snapshot --no-owner --exit-on-error"
psql_in_db -d snapshot -c "UPDATE articles SET lead = NULL WHERE lead IS NOT NULL"
docker compose exec -T db pg_dump -U datos -d snapshot -Fc --no-owner --no-privileges >"$out"
psql_in_db -d postgres -c "DROP DATABASE snapshot"
echo "{\"event\": \"snapshot_written\", \"path\": \"$out\", \"bytes\": $(wc -c <"$out" | tr -d ' ')}"

[[ "${1:-}" == "--no-upload" ]] && exit 0

# huggingface_hub is not a project dependency: it only runs here, pinned.
DATA_REPO=$DATA_REPO SPACE_REPO=$SPACE_REPO SNAPSHOT=$out \
  uv run --no-project --with "huggingface_hub==2.4.0" python - <<'EOF'
import os

from huggingface_hub import HfApi

api = HfApi()
data_repo, space_repo = os.environ["DATA_REPO"], os.environ["SPACE_REPO"]
api.create_repo(data_repo, repo_type="dataset", private=True, exist_ok=True)
api.upload_file(
    path_or_fileobj=os.environ["SNAPSHOT"],
    path_in_repo="datos.dump",
    repo_id=data_repo,
    repo_type="dataset",
    commit_message="Daily snapshot",
)
api.restart_space(space_repo)
print(f'{{"event": "snapshot_published", "dataset": "{data_repo}", "space_restarted": "{space_repo}"}}')
EOF
