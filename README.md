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
