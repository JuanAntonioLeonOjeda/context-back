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
| `src/datos/classification/` | `ArticleClassifier` port, rules as data (`data/classification/`), append-only storage, `python -m datos.classification classify-new` (ADR-0015); the sampler for hand labelling (`sample`); the own model of ADR-0016: `SetFitClassifier`, `train`, `learning-curve` and `evaluate` (the `ml` group, never in the API image); model trained on `train-set-v5` (five sectors) and evaluated on 2026-11-06: sector promoted by exception (ADR-0016 amendment), level stays with the rules; the model classifies the new articles every hour in the `worker` (`docker/worker.sh`), which runs on the Space since 2026-11-24 (ADR-0022 described the author's machine) | 🚧 |
| `src/datos/stories/` | embeddings of the recent articles (`python -m datos.stories embed`, `ml` group), same-story grouping across outlets (`group`, ADR-0020) and links from each story to the earlier one it continues (`link`, ADR-0021), immutable runs; read side `/communities/{id}/stories` and `/stories/{id}/tree`; the related news of any article, a chain back in time computed on request from the stored vectors (`/articles/{id}/related`, HNSW index of migration 0020); updated every hour by the `worker` (`docker/worker.sh`: embed, then group and link only when there are new vectors) | ✅ |
| `src/datos/indicators/` | the five INE indicators: client of the Tempus API, definitions, loader (`python -m datos.indicators load`, run weekly by the `collector`, on the Space too), append-only observations, read side and `/communities/{id}/indicators`; see `docs/indicators.md` | ✅ |
| `src/datos/voters/` | voter profiles (ADR-0024, ADR-0026): reader of the Infoelectoral zip of an election by municipality and its loader (`python -m datos.voters load-election --file …`, the zip is downloaded by hand), the INE's income by municipality (`load-income --year …`) and the percentages with higher education, aged 70 or over and born abroad (`load-education --year … --file 66620.csv --file 66623.csv`, `load-age --year … --file 66620.csv`, `load-born-abroad --year … --file 66621.csv`: the Censo anual table files downloaded by hand and read in one pass by one reader that a table layout describes), the dimensions a profile is made by (income, size in electors, education, age, born abroad) with their bands by equal census or fixed limits and the vote shares (pure), the curated candidature → party table, read side and `/communities/{id}/voters?by=income\|size\|education\|age\|born_abroad` | ✅ |
| `src/datos/organization/` | the organisation charts (ADR-0025): bodies of the State and the communities, who holds the head post of each executive and department on a day, and the competences the law gives each body, every row with its source; pure chart (complete or nothing, ordered by name), the readers of the curated CSVs with every problem reported at once, `python -m datos.organization load`, the read side and `/organization` and `/communities/{id}/organization` | 🚧 |
| `src/datos/api/` | FastAPI app factory and the per-request provider of readers; routers live in each module's `interface/` (or `routes.py`): `/health`, `/territories`, `/parties`, `/communities/{id}/governments`, `/communities/{id}/indicators`, `/communities/{id}/news`, `/articles/{id}/related`, `/communities/{id}/voters`, `/organization`, `/communities/{id}/organization`, `/sectors`, `/map/governments`, `/map/geometry` | ✅ |
| `src/datos/http.py`, `src/datos/clock.py` | shared bounded HTTP client (honest user agent, size cap); the clock (today in Spain) | ✅ |
| `src/datos/config.py`, `src/datos/main.py` | settings and composition root | ✅ |
| `migrations/` | versioned SQL migrations (`0001`: reference data and news metadata; `0002`: per-territory competences; `0003`: outlet LLM flag; `0004`: downloads, indicators and append-only observations; `0005`: append-only classifications; `0006`: scores of a model's classifications; `0007`: sector `is_active`; `0008`: tags of an article; `0009`: the place of a tag in its article; `0010`: embeddings, story runs and stories; `0011`: story links and tree runs; `0012`: double precision scores; `0013`: the start date of a story run; `0014`: the indicator of a sector; `0015`: elections, municipal results and votes, municipal income, append-only; `0016`: organisation bodies, their holders and competences; `0017`: municipal values of a profile dimension and the file each load came from, append-only; `0018`: the same file can be loaded for more than one year; `0019`: age and place of birth as dimensions; `0020`: HNSW index on the embeddings for the related news) | 🚧 |
| `data/territories/` | territories CSV from INE, with its source in `README.md` | ✅ |
| `data/governments/` | curated parties (with their standard colour, from Wikidata), government terms since 2020, sectors and competences, with sources | ✅ |
| `data/geo/` | `ccaa.geojson`: the 19 communities simplified for the map, from the IGN (CC BY 4.0), with its build and attribution in `README.md` | ✅ |
| `data/classification/` | the terms of the rules classifier as CSV (`places`, `levels`, `sectors`, `exclusions`), with the matching conventions and the coverage of the last run in `README.md`; the rules' version is a hash of these files; `tag-stoplist.csv`: the article tags the model never reads (outlet markers, bylines), outside the rules' version | 🚧 |
| `data/sampling/`, `data/labelling/` | how articles are drawn for hand labelling (`python -m datos.classification sample`): equal per outlet, half random and half enriched by broad sector terms, seeded, disjoint from every labelled set; the Label Studio interface from the labelling guide | 🚧 |
| `data/eval/`, `docs/labelling-guide.md` | blind test set (200 hand-labelled articles, never used for training) and the evaluation reports; the guide is done and the set is labelled (two passes of the guide pending: the 5 unsure and 20 relabelled) | 🚧 |
| `tests/` | `unit/`, `integration/`, `fixtures/` (trimmed real feeds, sitemaps, section pages and article-page metadata) | 🚧 |
| `docker-compose.yml`, `Dockerfile`, `docker/`, `.dockerignore` | PostgreSQL with pgvector, Label Studio (profile `app`); pgAdmin is shared by all local projects and lives outside the repo (`../../pgadmin`); profile `app`: `back-main` (the API; on start it applies the migrations and loads the CSV data, `docker/entrypoint.sh`), `collector` (`docker/collector.sh`) (same image; every 3 hours collects the feeds and classifies the new articles, and every `INDICATORS_INTERVAL_DAYS` days (7) loads the INE indicators, logs JSON to stdout), `worker` (`docker/worker.Dockerfile`, `docker/worker.sh`: the `ml` group with CPU torch and the encoder baked in; every hour classifies with the own model, embeds, groups and links) and `front` (built from `../front`); the Compose project is `datos` | ✅ |
| `scripts/` | `collect-news.sh` (one collection run, JSON logs in `var/log/`), `launchd/` schedule template (replaced by the `collector` service), `learning-curve.sh` (the learning curve of ADR-0016 on your machine, each point stored when it ends), `show-curve.sh` (the points measured so far as a table, read-only), `train-model.sh`, `colab-dump.sh` + `train-colab.ipynb` (the same training on a free Google Colab GPU: the notebook clones the branch and restores the database dump), `classify-with-model.sh`, `update-stories.sh` and `publish-snapshot.sh` (the model's classification, the stories and the snapshot on this machine through `launchd/`; unloaded since 2026-11-24, when the Space took those jobs over: kept to run them by hand) | ✅ |
| `deploy/huggingface/` | the public Space (ADR-0023): one image with PostgreSQL, the API, the web app behind nginx on port 7860, the collector and the worker (`Dockerfile`, `nginx.conf`, `start.sh`: restores the database from the private dataset on start, then runs both jobs; `backup.py`: the whole database back to the dataset after each job's cycle, since the Space's disk is not persistent); the Space is the only writer since 2026-11-24, the Space card (`README.md`) and `build_space.sh` (both repos' last commits into one folder); deployed by `.github/workflows/deploy-space.yml` on a push to `main` | ✅ |
| `.env.example` | every environment variable, documented | ✅ |
| `.github/workflows/` | `ci.yml`: ruff, mypy, unit + integration tests (green on GitHub); `deploy-space.yml` and `keep-space-awake.yml`: the Space (ADR-0023) | ✅ |
| `docs/sources-audit.md` | dated audit of feeds, robots.txt, mining reservations, GDELT, INE, elections, IP law | ✅ |
| `data/news/` | approved outlets and how each is collected | ✅ |
| `data/organization/` | `bodies.csv`, `holders.csv`, `competences.csv`: the organisation charts, curated by hand with one source URL per row (the State from the BOE; Madrid, Canarias and Cataluña as the pilot; Andalucía, Castilla-La Mancha and the Comunitat Valenciana since 2026-11-26), with the conventions in `README.md` | 🚧 |
| `data/voters/` | `candidature-parties.csv`: which party a candidature of an election counts as (by candidature; a coalition has no row), with its rule in `README.md` | ✅ |
| `docs/project-brief.md` | scope, architecture, data model, phases, sources to verify | ✅ |
| `docs/indicators.md` | the five indicators: INE table, unit, frequency, how a value is chosen and stored, what was verified | ✅ |
| `docs/adr/` | Architecture Decision Records: 0001–0022 (0013 lives in `../front/docs/adr/`; 0005 and 0014 superseded by 0018), 0023 proposed, 0024 accepted, 0026 proposed, index in `docs/adr/README.md`, template in `docs/adr/template.md` | ✅ |
| `specs/<phase>/` | `spec.md`, `plan.md`, `tasks.md` for each phase (workflow `spec-driven-phase`); `foundation`, `map-governments`, `news-live` and `context-voters` also have `review.md` | 🚧 |

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
