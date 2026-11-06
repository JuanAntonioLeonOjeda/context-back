#!/usr/bin/env bash
# Prepares in DEST what the Hugging Face Space builds (ADR-0023): this repo's last commit in back/,
# the web app's in front/, and the Space's Dockerfile and README at the top. Then it is uploaded
# with: hf upload Juanan237/incontext DEST . --repo-type space (the deploy-space workflow does it).
#
#   deploy/huggingface/build_space.sh DEST
#   FRONT_DIR=path deploy/huggingface/build_space.sh DEST    # the web app repo (default ../front)
#
# Only committed code goes in (git archive HEAD): what is uncommitted is never deployed.
set -euo pipefail

DEST=${1:?usage: $0 DEST}
BACK=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
FRONT=$(git -C "${FRONT_DIR:-$BACK/../front}" rev-parse --show-toplevel)
BACK_CODE=(pyproject.toml uv.lock README.md alembic.ini migrations src data deploy/huggingface)

for repo in "$BACK" "$FRONT"; do
  [[ -z $(git -C "$repo" status --porcelain --untracked-files=no) ]] \
    || echo "Note: $repo has uncommitted changes; the last commit is used" >&2
done

mkdir -p "$DEST"
# Only what this script writes is removed, so the .git of a Space clone is left alone.
rm -rf "${DEST:?}/back" "${DEST:?}/front" "$DEST/Dockerfile" "$DEST/README.md"
mkdir -p "$DEST/back" "$DEST/front"

git -C "$BACK" archive HEAD "${BACK_CODE[@]}" | tar -x -C "$DEST/back"
git -C "$FRONT" archive HEAD | tar -x -C "$DEST/front"
cp "$BACK/deploy/huggingface/Dockerfile" "$BACK/deploy/huggingface/README.md" "$DEST/"

echo "Space ready in $DEST ($(du -sh "$DEST" | cut -f1)); back $(git -C "$BACK" rev-parse --short HEAD), front $(git -C "$FRONT" rev-parse --short HEAD)"
