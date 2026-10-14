# The API and its one-shot jobs (migrations, data loading, INE indicators): one image, run
# with different commands by docker-compose.yml (profile `app`).
FROM python:3.13-slim-trixie

# uv, pinned to the version the project is developed with.
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Dependencies first: this layer is rebuilt only when pyproject.toml or uv.lock change.
# `--no-default-groups` leaves out dev tools and shapely (geometry build only, not runtime).
# README.md: pyproject.toml declares it as the package readme, so the build needs it.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-default-groups --no-install-project

COPY alembic.ini ./
COPY migrations ./migrations
COPY src ./src
COPY data ./data
RUN uv sync --locked --no-default-groups

# Not root: nothing in the API or the jobs needs it.
RUN useradd --system --no-create-home --uid 10001 app
USER app

EXPOSE 8000
CMD ["uvicorn", "datos.main:app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
