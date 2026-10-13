#!/usr/bin/env bash
# Collects news once: starts the database if needed, runs the collector, and leaves the
# database as it found it. Meant for a scheduler (scripts/launchd/); logs are JSON lines
# in var/log/collect-news.log.
set -euo pipefail

cd "$(dirname "$0")/.."
export PATH="$HOME/.docker/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
mkdir -p var/log
log=var/log/collect-news.log

if ! docker info >/dev/null 2>&1; then
  printf '{"event": "collection_not_started", "reason": "docker not running", "at": "%s"}\n' \
    "$(date -u +%FT%TZ)" >>"$log"
  exit 1
fi

was_running=$(docker compose ps --status running --services | grep -qx db && echo yes || echo no)
docker compose up -d --wait db >/dev/null 2>&1

status=0
LOG_JSON=true uv run --frozen python -m datos.news collect >>"$log" 2>&1 || status=$?

if [ "$was_running" = no ]; then
  docker compose stop db >/dev/null 2>&1
fi
exit "$status"
