# datos — backend

Backend and data pipeline of a portal that puts Spanish regional political news in
context. Work in progress; see `docs/project-brief.md` and `docs/adr/`.

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
| `pgadmin` | database browser; the server "datos (local)" is preconfigured, password `datos` | http://localhost:5050 |

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
