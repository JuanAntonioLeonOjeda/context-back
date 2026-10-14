#!/bin/sh
# Starts the API. Before it listens it brings the database up to date: the migrations and the
# versioned CSV data (territories, parties, governments). Both are idempotent, so restarting
# the container is how the CSV data is reloaded after an edit.
set -e
alembic upgrade head
python -m datos.territories load
python -m datos.governments load
exec "$@"
