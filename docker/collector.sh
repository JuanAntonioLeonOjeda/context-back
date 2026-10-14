#!/bin/sh
# The `collector` service: collects the feeds, classifies the new articles, sleeps, repeats.
# Runs from the first start and then every COLLECT_INTERVAL_MIN minutes (default 180, the
# politeness limit of docs/sources-audit.md: a feed is read at most every few hours).
# A failed step is logged and does not stop the loop; the next cycle tries again. Logs are
# JSON lines on stdout (`docker compose logs collector`); the commands log their own events.
set -u

interval_min="${COLLECT_INTERVAL_MIN:-180}"

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
  fi
}

# `sleep` in the foreground would delay the stop signal by up to the whole interval.
trap 'event collector_stopped; exit 0' TERM INT

event collector_started
while true; do
  step collection python -m datos.news collect
  step classification python -m datos.classification classify-new
  sleep $((interval_min * 60)) &
  wait $!
done
