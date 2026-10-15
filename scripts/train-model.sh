#!/usr/bin/env bash
# Train the own classifier on your machine, with the progress in the terminal (ADR-0016).
#
#   scripts/train-model.sh                  # seed 42: install `ml`, start the database, show the plan, ask, train
#   scripts/train-model.sh --seed 7         # any `train` flag goes through (see the README)
#   scripts/train-model.sh --num-iterations 5
#
# Nothing is piped, so SetFit's progress bars stay visible.
set -euo pipefail

cd "$(dirname "$0")/.."
export PATH="$HOME/.docker/bin:$PATH"

args=("$@")
if [[ ! " ${args[*]:-} " =~ " --seed " ]]; then
  args+=(--seed 42)
fi

uv sync --group ml
docker compose up -d --wait db

echo "== Plan (nothing is trained or stored yet) =="
uv run python -m datos.classification train "${args[@]}" --dry-run

read -r -p "Train with this plan? [y/N] " answer
[[ "$answer" =~ ^[yY]$ ]] || { echo "Cancelled."; exit 0; }

uv run python -m datos.classification train "${args[@]}"
