# The `worker` service: the jobs that need the `ml` group (the own classifier and the sentence
# encoder of the stories), which never go into the API image (ADR-0016). It runs worker.sh: classify
# the new articles with the own model, then bring the stories and their trees up to date.
FROM python:3.13-slim-trixie

COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    HF_HOME=/opt/hf

WORKDIR /app

# The ml group with torch for CPU only (docker/uv-sync-ml.sh says why).
COPY pyproject.toml uv.lock README.md ./
COPY --chmod=755 docker/uv-sync-ml.sh /usr/local/bin/uv-sync-ml.sh
RUN uv-sync-ml.sh --no-install-project

# The stories' encoder in the image, so a run never reaches the Hub (on 2026-11-16 that check hung
# for a day) and every deploy has the same weights.
ARG ENCODER=sentence-transformers/paraphrase-multilingual-mpnet-base-v2
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${ENCODER}')"
ENV HF_HUB_OFFLINE=1

COPY alembic.ini ./
COPY migrations ./migrations
COPY src ./src
COPY data ./data
COPY --chmod=755 docker/worker.sh /usr/local/bin/worker.sh
RUN uv-sync-ml.sh

RUN useradd --system --no-create-home --uid 10001 app && chmod -R a+rX /opt/hf
USER app

ENTRYPOINT ["worker.sh"]
