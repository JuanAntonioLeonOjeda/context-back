#!/bin/sh
# The `worker` service: every WORKER_INTERVAL_MIN minutes (default 60) it classifies the new
# articles with the own model (ADR-0016: the model gives the sectors, the rules the rest, stored as
# `composite`), embeds them, and groups and links the stories only when an article was embedded
# after the latest grouping (each grouping copies every story of the last 60 days). The same steps
# as scripts/classify-with-model.sh and scripts/update-stories.sh, without the author's machine.
# A failed step is logged and does not stop the loop. Logs are JSON lines on stdout.
set -u

interval_min="${WORKER_INTERVAL_MIN:-60}"
model_dir="${MODEL_DIR:?MODEL_DIR is the own model, mounted read-only}"
group_threshold="${GROUP_THRESHOLD:-0.88}"
link_threshold="${LINK_THRESHOLD:-0.75}"

event() {
  printf '{"event": "%s", "at": "%s"}\n' "$1" "$(date -u +%FT%TZ)"
}

step() {
  name="$1"
  shift
  if "$@"; then
    event "${name}_finished"
  else
    printf '{"event": "%s_failed", "exit_code": %s, "at": "%s"}\n' "$name" "$?" "$(date -u +%FT%TZ)"
    return 1
  fi
}

# Exit code 0 when an article was embedded after the latest grouping run.
embedded_since_last_run() {
  python - <<'PY'
import sys

from sqlalchemy import create_engine, text

from datos.config import load_settings

query = text(
    "SELECT exists (SELECT 1 FROM article_embeddings WHERE created_at >"
    " coalesce((SELECT max(created_at) FROM story_runs), '-infinity'))"
)
with create_engine(str(load_settings().database_url)).connect() as connection:
    sys.exit(0 if connection.execute(query).scalar() else 1)
PY
}

update_stories() {
  step embedding python -m datos.stories embed || return 1
  if ! embedded_since_last_run; then
    event stories_unchanged
    return 0
  fi
  step grouping python -m datos.stories group --threshold "$group_threshold" &&
    step linking python -m datos.stories link --threshold "$link_threshold"
}

trap 'event worker_stopped; exit 0' TERM INT

[ -f "$model_dir/model-card.json" ] || { event "no_model_in_${model_dir}"; exit 1; }
event worker_started
while true; do
  step classification python -m datos.classification classify-new --model "$model_dir"
  update_stories
  sleep $((interval_min * 60)) &
  wait $!
done
