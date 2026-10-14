# datos — backend

Backend and data pipeline of a portal that puts Spanish regional political news in
context. Work in progress; see `docs/project-brief.md` and `docs/adr/`.

## Run everything

With Docker Desktop and the `front` repository next to this one (`datos/back`, `datos/front`):

```bash
docker compose --profile app up -d --build
```

- **Web app:** http://localhost:3000
- **API and its docs:** http://localhost:8000/docs
- The first start builds the images, applies the migrations and loads the territories,
  governments and parties. A background job then reads the INE indicators (about a minute;
  the map works without it).
- Stop: `docker compose --profile app down` (the data stays in the `db-data` volume).
- Only the database, to develop the API locally: `docker compose up -d db`.
- Reload the CSV data after editing it: `docker compose --profile app run --rm migrate`.
