# datos — backend

Backend and data pipeline of a portal that puts Spanish regional political news in
context. Work in progress; see `docs/project-brief.md` and `docs/adr/`.

## MAIN DEPENDENCIES
![Python](https://img.shields.io/badge/PYTHON-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FASTAPI-0.143.0-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Uvicorn](https://img.shields.io/badge/UVICORN-0.54.0-black?style=for-the-badge&logo=gunicorn&logoColor=white)
![Pydantic](https://img.shields.io/badge/PYDANTIC%20SETTINGS-2.15.0-E92063?style=for-the-badge&logo=pydantic&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLALCHEMY-2.1.4-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)
![Alembic](https://img.shields.io/badge/ALEMBIC-1.20.0-black?style=for-the-badge)
![Psycopg](https://img.shields.io/badge/PSYCOPG-3.3.6-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/POSTGRESQL-17-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![pgvector](https://img.shields.io/badge/PGVECTOR-0.8.2-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![HTTPX](https://img.shields.io/badge/HTTPX-0.28.1-black?style=for-the-badge)
![Feedparser](https://img.shields.io/badge/FEEDPARSER-6.0.14-FFA500?style=for-the-badge&logo=rss&logoColor=white)
![Structlog](https://img.shields.io/badge/STRUCTLOG-26.1.0-black?style=for-the-badge)
![Shapely](https://img.shields.io/badge/SHAPELY-2.2.0-black?style=for-the-badge)
![SetFit](https://img.shields.io/badge/SETFIT-1.2.0-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)
![Sentence Transformers](https://img.shields.io/badge/SENTENCE%20TRANSFORMERS-5.7.0-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)
![Docker](https://img.shields.io/badge/DOCKER-COMPOSE-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Label Studio](https://img.shields.io/badge/LABEL%20STUDIO-1.23.0-black?style=for-the-badge)

Shapely is only needed to build the map geometry; SetFit and Sentence Transformers belong to the
optional `ml` group and never ship in the API image. Dev tools: uv, Ruff 0.17.0, mypy 2.4.0, pytest
9.1.1, Testcontainers.

## Run everything

With Docker Desktop and the `front` repository next to this one (`datos/back`, `datos/front`):

```bash
docker compose --profile app up -d --build
```

The Compose project is called `datos`: it is the whole system, not only this repository.

| Service | What it is | Address |
|---|---|---|
| `front` | the web app (nginx serves it and forwards `/api` to `back-main`) | http://localhost:3000 |
| `back-main` | the API; on start it applies the migrations and loads the CSV data | http://localhost:8000/docs |
| `db` | PostgreSQL with pgvector | `localhost:5432` |

- Database browser: one pgAdmin shared by all local projects, in `../../pgadmin` (`docker compose up -d` there; http://localhost:5050; the server "datos (local)" is preconfigured, password `datos`). Start it first: `pgadmin-net` is the network it creates.
- Stop: `docker compose --profile app down` (the data stays in the `datos_db-data` volume).
- Only the database, to develop the API locally: `docker compose up -d db`.
- Reload the CSV data after editing it: `docker compose --profile app restart back-main`.
- Load the INE indicators (about a minute; the map works without them and the community card
  needs them): `docker compose --profile app exec back-main python -m datos.indicators load`.

## Train the own model

The own classifier (ADR-0016) is trained on your machine, not in Docker, and needs the `ml` group
(about 1 GB; never in the API image). The database must be up (`docker compose up -d db`): the
training reads the headlines and leads of the labelled articles by id.

```bash
uv sync --group ml                       # once: SetFit, torch, the encoder's libraries

# 1. See what it would do, without training (examples, labels, sentence pairs, time):
uv run python -m datos.classification train --seed 42 --dry-run

# 2. Train. SetFit's progress bar and loss lines appear in the terminal; Ctrl+C stores nothing:
uv run python -m datos.classification train --seed 42
```

`scripts/train-model.sh [train flags]` does the same in one go: installs the group, starts the
database, shows the plan, asks, and trains with the progress visible.

- `--training-set PATH` (default `data/train/train-set-v1.jsonl`), `--encoder NAME` (default the
  one of ADR-0016), `--num-iterations N` (sentence pairs per example, default 20), `--models-dir`
  (default `models/`, out of git).
- The model is saved as `models/<training set>-<encoder>-seed<seed>/` with a `model-card.json`:
  everything needed to repeat the training. A stored model is never overwritten: a new seed or a
  new training set gives a new directory.
- It refuses a training set with a repeated article, an article missing from the database or one
  that is also in the blind test set (`data/eval/`), before anything is trained.
- Time, measured on 2026-10-15 on the author's Mac (Apple GPU, `mps`): about 9 s per step of 16
  sentence pairs. With 400 examples and 20 iterations that is 16,000 pairs, about 2.4 hours; the
  dry run gives the figure for the actual set. The first run also downloads the encoder
  (about 1.2 GB) into `~/.cache/huggingface`.
- The real SetFit tests are `uv run pytest -m ml` (a few minutes); CI never runs them.

## The learning curve

Before labelling more, it answers one question: does the model still improve with more labels? It
trains on nested subsets of 100, 200 and 300 labelled articles and scores each model on the part
held out (never the blind test set). The training set is split in 4 folds by stratum, and two are
measured (decided in ADR-0016, D11 and D12): about 7 hours with mpnet, one night.

```bash
scripts/learning-curve.sh                    # the plan, then asks; seed 42, folds 0 and 1
scripts/learning-curve.sh --run-folds 2 3    # add the other two folds another day
uv run python -m datos.classification learning-curve --seed 42 --dry-run   # the plan only
```

- Each point is stored in `models/<set>-<encoder>-seed<seed>-curve.jsonl` as soon as it ends, and one
  line is printed (fold, size, time, macro-F1 per family and label). Run again after a cut and it
  carries on from the file. It refuses points measured with other settings: a curve from two
  different trainings says nothing.
- At the end, a table per family (mean and each fold's score) and the rule decided before seeing any
  curve: label 100 more if the mean macro-F1 rises at least 3 points from 200 to 300 in either family.
  "Cannot be told yet" means no fold reached both sizes.
- With 400 labels there is no point at 400: some articles are always held out.

