#!/usr/bin/env bash
# The learning curve inside the training set, on your machine, with the progress in the terminal
# (ADR-0016, D11 and D12). Two of four folds, subsets of 100, 200 and 300: about 7 hours with
# mpnet, one night. Each point is stored when it ends, so it can be cut and run again.
#
#   scripts/learning-curve.sh                       # seed 42, folds 0 and 1
#   scripts/learning-curve.sh --run-folds 2 3       # add the other two folds another day
#   scripts/learning-curve.sh --sizes 100 200       # any `learning-curve` flag goes through
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
uv run python -m datos.classification learning-curve "${args[@]}" --dry-run

read -r -p "Measure with this plan? [y/N] " answer
[[ "$answer" =~ ^[yY]$ ]] || { echo "Cancelled."; exit 0; }

uv run python -m datos.classification learning-curve "${args[@]}"
