# AGENTS.md — Regional news context portal (backend)

Route index.

Project context, scope, phases, commands, neutrality rules and what not to do live in
`.claude/rules/project-policies.md`. How the assistant must collaborate (design first,
explain, core zones written together) lives in `.claude/rules/ai-collaboration.md`. Both
are always loaded with this index. The full brief is `docs/project-brief.md`. The web app
is the sibling repo `../front`; ADRs for the whole project live here, in `docs/adr/`.

## Code map

Status: ⏳ planned (does not exist yet) · 🚧 in progress · ✅ done.
Update the status column when a phase creates or finishes a path.

| Path | Content | Status |
|---|---|---|
| `pyproject.toml`, `uv.lock` | project, dependencies and tool config (ruff, mypy, pytest) | ✅ |
| `src/datos/territories/` | State anchor, communities and provinces with INE codes; CSV loader (`python -m datos.territories load`); reader and `/territories`; boundaries read from the IGN GML and built into `data/geo/ccaa.geojson` (`python -m datos.territories build-geometry`, needs the `geo` group) and served at `/map/geometry` | ✅ |
| `src/datos/governments/` | parties, government terms, sectors and competences (with per-territory rows), rules, CSV loader (`python -m datos.governments load`); read side: government in force on a date, the map's governing parties, routers `/communities/{id}/governments`, `/map/governments` and `/parties` | ✅ |
| `src/datos/news/` | outlets, collector for RSS, news sitemaps and section pages (`python -m datos.news collect`), article cleaning; the outlet's tags from the feeds and from the pages that carry them (read only where the site allows it, checked on every run; `backfill-page-tags`); read side: latest news of a community and sector (no party, ADR-0018), `/communities/{id}/news`; history pending | 🚧 |
| `src/datos/classification/` | `ArticleClassifier` port, rules as data (`data/classification/`), append-only storage, `python -m datos.classification classify-new` (ADR-0015); the sampler for hand labelling (`sample`); the own model of ADR-0016: `SetFitClassifier`, `train` and `learning-curve` (the `ml` group, never in the API image); weights wait for the labels | 🚧 |
| `src/datos/stories/` | same-story grouping across outlets, links between stories | ⏳ |
| `src/datos/indicators/` | the five INE indicators: client of the Tempus API, definitions, loader (`python -m datos.indicators load`), append-only observations, read side and `/communities/{id}/indicators`; see `docs/indicators.md` | ✅ |
| `src/datos/voters/` | election results ETL and voter profiles | ⏳ |
| `src/datos/api/` | FastAPI app factory and the per-request provider of readers; routers live in each module's `interface/` (or `routes.py`): `/health`, `/territories`, `/parties`, `/communities/{id}/governments`, `/communities/{id}/indicators`, `/communities/{id}/news`, `/map/governments`, `/map/geometry` | ✅ |
| `src/datos/http.py`, `src/datos/clock.py` | shared bounded HTTP client (honest user agent, size cap); the clock (today in Spain) | ✅ |
| `src/datos/config.py`, `src/datos/main.py` | settings and composition root | ✅ |
| `migrations/` | versioned SQL migrations (`0001`: reference data and news metadata; `0002`: per-territory competences; `0003`: outlet LLM flag; `0004`: downloads, indicators and append-only observations; `0005`: append-only classifications; `0006`: scores of a model's classifications; `0007`: sector `is_active`; `0008`: tags of an article; `0009`: the place of a tag in its article) | 🚧 |
| `data/territories/` | territories CSV from INE, with its source in `README.md` | ✅ |
| `data/governments/` | curated parties (with their standard colour, from Wikidata), government terms since 2020, sectors and competences, with sources | ✅ |
| `data/geo/` | `ccaa.geojson`: the 19 communities simplified for the map, from the IGN (CC BY 4.0), with its build and attribution in `README.md` | ✅ |
| `data/classification/` | the terms of the rules classifier as CSV (`places`, `levels`, `sectors`, `exclusions`), with the matching conventions and the coverage of the last run in `README.md`; the rules' version is a hash of these files; `tag-stoplist.csv`: the article tags the model never reads (outlet markers, bylines), outside the rules' version | 🚧 |
| `data/sampling/`, `data/labelling/` | how articles are drawn for hand labelling (`python -m datos.classification sample`): equal per outlet, half random and half enriched by broad sector terms, seeded, disjoint from every labelled set; the Label Studio interface from the labelling guide | 🚧 |
| `data/eval/`, `docs/labelling-guide.md` | blind test set (200 hand-labelled articles, never used for training); the guide is done, the set waits for ~3 weeks of collection | 🚧 |
| `tests/` | `unit/`, `integration/`, `fixtures/` (trimmed real feeds, sitemaps, section pages and article-page metadata) | 🚧 |
| `docker-compose.yml`, `Dockerfile`, `docker/`, `.dockerignore` | PostgreSQL with pgvector, Label Studio, pgAdmin (profiles `app` and `tools`); profile `app`: `back-main` (the API; on start it applies the migrations and loads the CSV data, `docker/entrypoint.sh`), `collector` (`docker/collector.sh`) (same image; every 3 hours collects the feeds and classifies the new articles, logs JSON to stdout) and `front` (built from `../front`); the Compose project is `datos` | ✅ |
| `scripts/` | `collect-news.sh` (one collection run, JSON logs in `var/log/`), `launchd/` schedule template (replaced by the `collector` service), `learning-curve.sh` (the learning curve of ADR-0016 on your machine, each point stored when it ends), `show-curve.sh` (the points measured so far as a table, read-only), `train-model.sh`, `classify-with-model.sh` (hourly through `launchd/`: the model's classification on this machine) | ✅ |
| `.env.example` | every environment variable, documented | ✅ |
| `.github/workflows/ci.yml` | ruff, mypy, unit + integration tests (green on GitHub) | ✅ |
| `docs/sources-audit.md` | dated audit of feeds, robots.txt, mining reservations, GDELT, INE, elections, IP law | ✅ |
| `data/news/` | approved outlets and how each is collected | ✅ |
| `docs/project-brief.md` | scope, architecture, data model, phases, sources to verify | ✅ |
| `docs/indicators.md` | the five indicators: INE table, unit, frequency, how a value is chosen and stored, what was verified | ✅ |
| `docs/adr/` | Architecture Decision Records: 0001–0015 accepted (0013 lives in `../front/docs/adr/`), index in `docs/adr/README.md`, template in `docs/adr/template.md` | ✅ |
| `specs/<phase>/` | `spec.md`, `plan.md`, `tasks.md` for each phase (workflow `spec-driven-phase`); `foundation` and `map-governments` also have `review.md` | 🚧 |

Dependency rule between layers and modules: `.claude/rules/architecture.md`.

## `.claude/` map and agent config

| Path | What it holds |
|---|---|
| `.claude/settings.json` | team permissions: allowed read-only/dev commands, `.env` blocked |
| `.claude/rules/project-policies.md` | context, phases, commands, licences, neutrality, what not to do |
| `.claude/rules/ai-collaboration.md` | the AI-assisted working agreement: design first, explain, collaborative core zones, small commits |
| `.claude/rules/architecture.md` | data flow, module layout, ports & adapters, reproducibility |
| `.claude/rules/code-style.md` | Python 3.12, mypy strict, ruff, Pydantic at the edges, errors, logging, config |
| `.claude/rules/naming-conventions.md` | files, types, units and dates, INE codes, parties, database, API |
| `.claude/rules/atomic-functions-solid.md` | atomic functions and the SOLID that applies here |
| `.claude/rules/testing-conventions.md` | pytest, Testcontainers, real fixtures, the blind test set |
| `.claude/rules/core-zones.md` | (path-scoped) classification, stories, indicators, voters, schema: collaborative mode |
| `.claude/rules/db-migrations.md` | (path-scoped) migrations immutable once merged; append-only observations; idempotent writes |
| `.claude/skills/news-sources/` | verified facts on outlets, collection paths, IP limits, LLM restrictions, GDELT bias, INE tables |
| `.claude/agents/py-reviewer.md` | project reviewer (read-only): boundaries, layers, edges, reproducibility, typing |
| `.claude/agents/neutrality-reviewer.md` | neutrality reviewer (read-only): same path for every party and outlet, parties only through official facts, wording |
| `.claude/agents/code-reviewer.md` | generic reviewer (read-only): security, correctness, performance, maintainability |
| `.claude/commands/create-pr.md` | `/create-pr`: PR with `gh`, conventional commit, generated description |
| `.claude/commands/new-adr.md` | `/new-adr <title>`: ADR skeleton that the author fills in |
| `.claude/commands/defend.md` | `/defend <path or topic>`: interview-style questions on a piece of the system |
| `.claude/workflows/spec-driven-phase.md` | plan (and wait) → spec → plan → tasks → implementation → tests → review → ADR (`/defend` optional) |
| `.claude/workflows/git-workflow.md` | `main`/`develop`, branch naming, Conventional Commits, small atomic commits |
| `.claude/workflows/architecture-decision.md` | when an ADR is needed and how to write one together |
