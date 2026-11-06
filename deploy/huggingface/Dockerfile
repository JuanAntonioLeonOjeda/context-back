# Image for the Hugging Face Space: PostgreSQL, the API and the web app in one container, on port
# 7860 (ADR-0023). Built from the folder that deploy/huggingface/build_space.sh prepares: this
# repo's code in back/ and the web app's in front/. The data is not in the image: on start,
# start.sh downloads the latest snapshot from a private Hugging Face dataset.

FROM node:24-alpine AS front
WORKDIR /app
# pnpm at the version the web app is developed with (its package.json "packageManager").
RUN npm install --global pnpm@12.11.2
COPY front/package.json front/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY front/ .
# VITE_API_BASE_URL defaults to "/api", which nginx forwards to the API below.
RUN pnpm build

FROM python:3.13-slim-trixie

# PostgreSQL 17 with pgvector and nginx from Debian (trixie: 17.11, pgvector 0.8.0, nginx 1.26);
# curl downloads the snapshot.
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-17 postgresql-17-pgvector nginx curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:/usr/lib/postgresql/17/bin:$PATH"

# Spaces runs the container as uid 1000; PostgreSQL and nginx run as that user too.
RUN useradd --create-home --uid 1000 user
WORKDIR /app

# The same layers as the API image (Dockerfile in the repo root): no dev tools, no ml group.
COPY back/pyproject.toml back/uv.lock back/README.md ./
RUN uv sync --locked --no-default-groups --no-install-project
COPY back/alembic.ini ./
COPY back/migrations ./migrations
COPY back/src ./src
COPY back/data ./data
RUN uv sync --locked --no-default-groups

COPY --from=front /app/dist /app/web
COPY back/deploy/huggingface/nginx.conf /etc/nginx/space.conf
COPY --chmod=755 back/deploy/huggingface/start.sh /usr/local/bin/start.sh

ENV DATABASE_URL=postgresql+psycopg://user@127.0.0.1:5432/datos \
    LOG_JSON=true \
    PGDATA=/home/user/pgdata

USER user
EXPOSE 7860
CMD ["start.sh"]
