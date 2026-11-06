#!/usr/bin/env bash
# Brings the stories up to date: embeds the recent articles that have no vector yet, groups them
# into stories (ADR-0020) and links each story to the earlier one it continues (ADR-0021). Each
# grouping and linking is a new immutable run, and the API reads the latest one.
# Embedding needs the `ml` group, so it runs on this machine and not in Docker (as ADR-0022).
# Meant for a scheduler (scripts/launchd/es.datos.update-stories.plist), before the daily snapshot
# (scripts/publish-snapshot.sh); logs are JSON lines in var/log/update-stories.log.
#
#   scripts/update-stories.sh
#   GROUP_THRESHOLD=0.9 LINK_THRESHOLD=0.7 scripts/update-stories.sh    # other provisional values
set -euo pipefail

cd "$(dirname "$0")/.."
export PATH="$HOME/.docker/bin:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
mkdir -p var/log
log=var/log/update-stories.log
# The provisional thresholds of ADR-0020 and ADR-0021, set by the author reading real groups and trees.
group_threshold="${GROUP_THRESHOLD:-0.88}"
link_threshold="${LINK_THRESHOLD:-0.75}"

fail() {
  printf '{"event": "stories_not_updated", "reason": "%s", "at": "%s"}\n' \
    "$1" "$(date -u +%FT%TZ)" >>"$log"
  exit 1
}

docker info >/dev/null 2>&1 || fail "docker not running"
docker compose up -d --wait db >/dev/null 2>&1 || fail "database not ready"

stories() { LOG_JSON=true uv run --frozen --group ml python -m datos.stories "$@" >>"$log" 2>&1; }

stories embed || fail "embed failed"
stories group --threshold "$group_threshold" || fail "group failed"
stories link --threshold "$link_threshold" || fail "link failed"
