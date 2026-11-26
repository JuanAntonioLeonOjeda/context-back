#!/bin/sh
# The `collector` service: collects the feeds, classifies the new articles, sleeps, repeats.
# Runs from the first start and then every COLLECT_INTERVAL_MIN minutes (default 180, the
# politeness limit of docs/sources-audit.md: a feed is read at most every few hours).
# The INE indicators are loaded on the first cycle and then every INDICATORS_INTERVAL_DAYS days
# (default 7): the INE publishes them by quarter or by year, and a load stores only the values
# that changed. The time of the last load lives in this loop, so a restart loads them once more.
# A failed step is logged and does not stop the loop; the next cycle tries again. Logs are
# JSON lines on stdout (`docker compose logs collector`); the commands log their own events.
set -u

interval_min="${COLLECT_INTERVAL_MIN:-180}"
indicators_every_s=$((${INDICATORS_INTERVAL_DAYS:-7} * 86400))
indicators_at=0 # epoch seconds of the last load; 0: never, so the first cycle loads them

event() {
  printf '{"event": "%s", "at": "%s"}\n' "$1" "$(date -u +%FT%TZ)"
}

# Returns the step's own status, so a caller can tell (no `set -e`: a failure never stops the loop).
step() {
  name="$1"
  shift
  if "$@"; then
    event "${name}_finished"
  else
    status=$?
    printf '{"event": "%s_failed", "exit_code": %s, "at": "%s"}\n' "$name" "$status" "$(date -u +%FT%TZ)"
    return "$status"
  fi
}

# `sleep` in the foreground would delay the stop signal by up to the whole interval.
trap 'event collector_stopped; exit 0' TERM INT

event collector_started
while true; do
  step collection python -m datos.news collect
  step classification python -m datos.classification classify-new
  now=$(date +%s)
  if [ $((now - indicators_at)) -ge "$indicators_every_s" ]; then
    # Retried next cycle when it fails: the time moves only after a load that worked.
    step indicators python -m datos.indicators load && indicators_at=$now
  fi
  # AFTER_CYCLE, when set, runs once the cycle's data is stored (the Space backs up there).
  [ -n "${AFTER_CYCLE:-}" ] && step after_cycle sh -c "$AFTER_CYCLE"
  sleep $((interval_min * 60)) &
  wait $!
done
