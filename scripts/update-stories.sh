#!/usr/bin/env bash
# Brings the stories up to date: embeds the recent articles that have no vector yet, groups them
# into stories (ADR-0020) and links each story to the earlier one it continues (ADR-0021). Each
# grouping and linking is a new immutable run, and the API reads the latest one.
# Embedding needs the `ml` group, so it runs on this machine and not in Docker (as ADR-0022).
# Meant for a scheduler (scripts/launchd/es.datos.update-stories.plist, every hour); logs are JSON
# lines in var/log/update-stories.log.
#
#   scripts/update-stories.sh
#   GROUP_THRESHOLD=0.9 LINK_THRESHOLD=0.7 scripts/update-stories.sh    # other provisional values
#   HF_HUB_OFFLINE=0 scripts/update-stories.sh      # first run on a machine: download the encoder
#   ALWAYS_REGROUP=1 scripts/update-stories.sh      # group and link even with no new article
set -euo pipefail

cd "$(dirname "$0")/.."
export PATH="$HOME/.docker/bin:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
mkdir -p var/log
log=var/log/update-stories.log
# The provisional thresholds of ADR-0020 and ADR-0021, set by the author reading real groups and trees.
group_threshold="${GROUP_THRESHOLD:-0.88}"
link_threshold="${LINK_THRESHOLD:-0.75}"
# The encoder is read from the local cache, never checked against the Hub: on 2026-11-16 the check
# hung on a dead TLS connection (the Mac slept) for more than a day, with no timeout. A new revision
# of the encoder would also change every vector, so it is a decision, not a side effect of a run.
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"
# No step may run longer than this: a hang is stopped and said in the log instead of blocking the
# next day's run. Three hours: the grouping query alone took 16 minutes on 2026-11-17 and grows with
# the square of the articles of the last 60 days; a run of about 5 hours was logged on 2026-11-11.
step_limit_seconds="${STEP_LIMIT_SECONDS:-10800}"

fail() {
  printf '{"event": "stories_not_updated", "reason": "%s", "at": "%s"}\n' \
    "$1" "$(date -u +%FT%TZ)" >>"$log"
  exit 1
}

# Runs a command with a time limit. Job control gives the command its own process group, so the
# watchdog stops uv and the Python process it started, not only uv.
set -m
within_limit() {
  "$@" &
  local pid=$!
  (sleep "$step_limit_seconds" && kill -TERM -- "-$pid" 2>/dev/null) &
  local watchdog=$!
  local status=0
  wait "$pid" || status=$?
  kill -- "-$watchdog" 2>/dev/null || true
  return "$status"
}

docker info >/dev/null 2>&1 || fail "docker not running"
docker compose up -d --wait db >/dev/null 2>&1 || fail "database not ready"

stories() {
  within_limit env LOG_JSON=true uv run --frozen --group ml python -m datos.stories "$@" >>"$log" 2>&1
}

stories embed || fail "embed failed or took more than ${step_limit_seconds} s"

# Run every hour, but a new grouping only when an article was embedded after the latest one: the
# collector brings articles every few hours, and each run is a new immutable copy of every story of
# the last 60 days (about 300 kB). ALWAYS_REGROUP=1 groups anyway, e.g. to try other thresholds.
newer=$(docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "
  SELECT exists (SELECT 1 FROM article_embeddings
                 WHERE created_at > coalesce((SELECT max(created_at) FROM story_runs), '"'"'-infinity'"'"'))"') \
  || fail "could not compare the embeddings with the latest run"
if [[ "$newer" != "t" && "${ALWAYS_REGROUP:-0}" != "1" ]]; then
  printf '{"event": "stories_unchanged", "reason": "no article embedded since the latest run", "at": "%s"}\n' \
    "$(date -u +%FT%TZ)" >>"$log"
  exit 0
fi

stories group --threshold "$group_threshold" || fail "group failed or took more than ${step_limit_seconds} s"
stories link --threshold "$link_threshold" || fail "link failed or took more than ${step_limit_seconds} s"
