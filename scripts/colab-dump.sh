#!/usr/bin/env bash
# Dump the database for training on Google Colab (scripts/train-colab.ipynb clones the code
# from GitHub; the article texts the `train` command reads only live in this database).
#
#   scripts/colab-dump.sh              # writes var/colab/datos.dump
#
# The embeddings and stored classifications are left out (schema only): training does not read them.
set -euo pipefail

cd "$(dirname "$0")/.."
export PATH="$HOME/.docker/bin:$PATH"

mkdir -p var/colab
docker compose up -d --wait db
docker compose exec -T db pg_dump -U datos -d datos -Fc --no-owner --no-privileges \
  --exclude-table-data=article_embeddings \
  --exclude-table-data=classifications \
  >var/colab/datos.dump

ls -lh var/colab/datos.dump
echo "Upload that file in the notebook (scripts/train-colab.ipynb)."
