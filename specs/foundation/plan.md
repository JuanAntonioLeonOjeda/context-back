# Phase 0 — foundation: plan

## Modules created in this phase

| Module | Layers | Content |
|---|---|---|
| `territories` | domain, infrastructure, interface (CLI) | `Territory` (INE code, name, level, parent), loader from a versioned CSV |
| `governments` | domain, application, infrastructure, interface (CLI) | `Party`, `GovernmentTerm`, `Competence`; term validation (no overlaps, no gaps); loaders |
| `news` | infrastructure only (minimal) | RSS collector used to build the test set: fetch, parse, store metadata idempotently |
| `api` | interface | FastAPI app with `/health` |
| `config.py`, `main.py` | — | settings and composition root |

Domain rules worth testing as pure functions: term overlap and gap detection, government
kind consistency (a coalition has ≥ 2 governing parties; minority with support has ≥ 1
external-support party), resolving the term in force on a given date.

## Schema (first migration)

```
territories(code PK, name, level, parent_code FK NULL)
parties(id PK slug, name, short_name, colour_hex)
government_terms(id PK, territory_code FK, president_name, kind, valid_from, valid_to NULL, source_url)
government_term_parties(term_id FK, party_id FK, role, PK(term_id, party_id))
competences(id PK, sector, activity, level, legal_basis, source_url)
outlets(id PK slug, name, home_url, scope, region_code NULL)
articles(id PK, outlet_id FK, url UNIQUE per outlet, published_at, fetched_at, headline, lead)
```

`level` is `state | ccaa | autonomous_city | province`. `kind` is
`single_party | coalition | minority_with_support | caretaker`. `role` is
`governing | external_support`. Enums are `text` with `CHECK` constraints (easier to
extend than Postgres enums). The `vector` extension is created now; no vector columns yet.

## Decisions

| Decision | Choice | Record |
|---|---|---|
| Migration tool | Alembic, operations written by hand, forward-only (no downgrades; fix forward) | ADR-0010 (Proposed) |
| Query layer | **Proposed:** SQLAlchemy Core 2.0 (no ORM) with `psycopg` 3; repositories write explicit SQL expressions | needs the author's yes; if a real trade-off, ADR-0011 |
| Reference data format | CSV under `data/`, one row per fact, with `source_url` column; loaders validate with Pydantic | plan only |
| CLI | `argparse` (stdlib): `uv run python -m datos.governments load` | plan only |
| Test set storage | ids, URLs and labels in git; headline and lead only in the local database | spec AC9 |

## Dependencies (to approve)

Runtime: `fastapi`, `uvicorn`, `pydantic-settings`, `sqlalchemy`, `psycopg[binary]`,
`alembic`, `structlog`, `httpx`, `feedparser`.
Dev: `ruff`, `mypy`, `pytest`, `testcontainers[postgres]`.

## Docker Compose

- `db`: PostgreSQL with pgvector (official `pgvector/pgvector` image, version pinned after
  checking the current tags), healthcheck with `pg_isready`, named volume.
- `labelstudio`: Label Studio (version pinned after checking), its own volume, healthcheck.

## Configuration (`.env.example`)

`DATABASE_URL`, `LOG_LEVEL`, `LABEL_STUDIO_PORT`. No LLM key in this phase.

## Sources audit method

- Outlets: candidate list by criterion (national outlets of varied editorial lines, the
  public broadcaster, one or two regional outlets per pilot community). For each: section
  feeds found, a fetch of each feed, items per day, presence of lead and date, terms of
  use and `robots.txt` notes.
- GDELT: query a sample week for the pilot communities and compare with the RSS items of
  the same week.
- INE: identify the table ids for population, income, education level and housing prices
  by community; one request each.
- Election results: where regional and general results by municipality are published.
- Output: `docs/sources-audit.md` (dated), skill `.claude/skills/news-sources/SKILL.md`
  (verified facts only).

## Blind test set method

1. The collector fetches the approved feeds for ~2 weeks (or until enough items exist).
2. A stratified sample of 200: by outlet, by pilot vs. non-pilot community, and including
   articles outside the three sectors (negatives).
3. `docs/labelling-guide.md`: definitions and edge cases for community, sector and
   government level, with examples from every party.
4. Label Studio project with that configuration; the author labels with no proposals
   loaded.
5. Export → `data/eval/test-set-v1.jsonl`. The file is frozen; a new version gets a new
   name.

## Risks

- Outlets without RSS → fewer outlets, or sitemaps (verify terms first).
- Government data errors → every row has a source; tests on overlaps and gaps; author
  review.
- Labelling fatigue → two sessions of 100; the guide resolves ambiguous cases before
  starting.
