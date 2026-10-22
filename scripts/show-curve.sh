#!/usr/bin/env bash
# The learning-curve points measured so far, as a table (ADR-0016, D11 and D12). Reads the
# results file that `scripts/learning-curve.sh` appends to; it does not train or touch the database.
#
#   scripts/show-curve.sh                           # the seed-42 mpnet curve
#   scripts/show-curve.sh --labels                  # add the F1 of every label
#   scripts/show-curve.sh path/to/other-curve.jsonl # any results file
set -euo pipefail

cd "$(dirname "$0")/.."

file="models/train-set-v1-paraphrase-multilingual-mpnet-base-v2-seed42-curve.jsonl"
labels=0
for arg in "$@"; do
  case "$arg" in
    --labels) labels=1 ;;
    *) file="$arg" ;;
  esac
done

[[ -f "$file" ]] || { echo "No results file at $file yet."; exit 1; }

python3 - "$file" "$labels" <<'PY'
import json
import sys
from collections import defaultdict

path, show_labels = sys.argv[1], sys.argv[2] == "1"
points = [json.loads(line) for line in open(path) if line.strip()]
points.sort(key=lambda p: (p["size"], p["fold"]))

by_size = defaultdict(list)
print(f"{path}: {len(points)} points\n")
print(f"{'size':>5} {'fold':>4} {'sector':>7} {'level':>7} {'time':>7}")
for p in points:
    macro = {s["family"]: s["macro_f1"] for s in p["scores"]}
    by_size[p["size"]].append(macro)
    print(
        f"{p['size']:>5} {p['fold']:>4} {macro['sector']:>7.3f} {macro['level']:>7.3f}"
        f" {p['training_seconds'] / 3600:>6.1f}h"
    )
    if show_labels:
        for s in p["scores"]:
            for label in s["labels"]:
                print(f"        {label['label']:<18} f1 {label['f1']:.3f}  {label['predicted']}/{label['support']} predicted")

print("\nMean per size (macro-F1)")
print(f"{'size':>5} {'folds':>5} {'sector':>7} {'level':>7}")
for size, rows in sorted(by_size.items()):
    sector = sum(r["sector"] for r in rows) / len(rows)
    level = sum(r["level"] for r in rows) / len(rows)
    print(f"{size:>5} {len(rows):>5} {sector:>7.3f} {level:>7.3f}")
PY
