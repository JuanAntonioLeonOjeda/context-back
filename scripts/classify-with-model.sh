#!/usr/bin/env bash
# Classifies the articles the own model has not seen yet (ADR-0016): the model gives the promoted
# families and the rules the rest, stored as the `composite` classifier. It needs the `ml` group, so
# it runs on this machine and not in Docker. Meant for a scheduler (scripts/launchd/); logs are JSON
# lines in var/log/classify-with-model.log.
#
#   MODEL_DIR=models/<name> scripts/classify-with-model.sh    # another model than the default
set -euo pipefail

cd "$(dirname "$0")/.."
export PATH="$HOME/.docker/bin:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
mkdir -p var/log
log=var/log/classify-with-model.log
model_dir="${MODEL_DIR:-models/train-set-v3-paraphrase-multilingual-mpnet-base-v2-seed42}"

fail() {
  printf '{"event": "classification_not_run", "reason": "%s", "at": "%s"}\n' \
    "$1" "$(date -u +%FT%TZ)" >>"$log"
  exit 1
}

[ -f "$model_dir/model-card.json" ] || fail "no model in $model_dir"
docker info >/dev/null 2>&1 || fail "docker not running"
docker compose up -d --wait db >/dev/null 2>&1 || fail "database not ready"

LOG_JSON=true uv run --frozen --group ml python -m datos.classification classify-new \
  --model "$model_dir" >>"$log" 2>&1
