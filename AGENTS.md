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
| `src/datos/territories/` | State anchor, communities and provinces with INE codes; CSV loader (`python -m datos.territories load`) | 🚧 |
| `src/datos/governments/` | parties, governments (coalitions, supports), terms, competence table | ⏳ |
| `src/datos/attribution/` | responsible party = competence × government in force on the date | ⏳ |
| `src/datos/news/` | outlets, RSS and history ingestion, article metadata | ⏳ |
| `src/datos/classification/` | `ArticleClassifier` port, rules, LLM adapter, own-model adapter | ⏳ |
| `src/datos/stories/` | same-story grouping across outlets, links between stories | ⏳ |
| `src/datos/indicators/` | official statistics ETL and derived indicators | ⏳ |
| `src/datos/voters/` | election results ETL and voter profiles | ⏳ |
| `src/datos/api/` | FastAPI routers and response models (`/health`) | 🚧 |
| `src/datos/config.py`, `src/datos/main.py` | settings and composition root | ✅ |
| `migrations/` | versioned SQL migrations (`0001`: reference data and news metadata) | 🚧 |
| `data/territories/` | territories CSV from INE, with its source in `README.md` | ✅ |
| `data/governments/` | curated governments and competences, with sources | ⏳ |
| `data/eval/` | hand-labelled blind test set (200 articles); never used for training | ⏳ |
| `tests/` | `unit/`, `integration/`, `fixtures/` | 🚧 |
| `docker-compose.yml` | PostgreSQL with pgvector, Label Studio | ✅ |
| `.env.example` | every environment variable, documented | ✅ |
| `.github/workflows/ci.yml` | ruff, mypy, unit + integration tests (not run yet: no remote) | 🚧 |
| `docs/project-brief.md` | scope, architecture, data model, phases, sources to verify | ✅ |
| `docs/adr/` | Architecture Decision Records (`NNNN-kebab-title.md`), index in `docs/adr/README.md`, template in `docs/adr/template.md` | 🚧 |
| `specs/<phase>/` | `spec.md`, `plan.md`, `tasks.md` for each phase (workflow `spec-driven-phase`) | ⏳ |

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
| `.claude/rules/core-zones.md` | (path-scoped) attribution, classification, stories, indicators, voters, schema: collaborative mode |
| `.claude/rules/db-migrations.md` | (path-scoped) migrations immutable once merged; append-only observations; idempotent writes |
| `.claude/agents/py-reviewer.md` | project reviewer (read-only): boundaries, layers, edges, reproducibility, typing |
| `.claude/agents/neutrality-reviewer.md` | neutrality reviewer (read-only): same path for every party and outlet, attribution rule, wording |
| `.claude/agents/code-reviewer.md` | generic reviewer (read-only): security, correctness, performance, maintainability |
| `.claude/commands/create-pr.md` | `/create-pr`: PR with `gh`, conventional commit, generated description |
| `.claude/commands/new-adr.md` | `/new-adr <title>`: ADR skeleton that the author fills in |
| `.claude/commands/defend.md` | `/defend <path or topic>`: interview-style questions on a piece of the system |
| `.claude/workflows/spec-driven-phase.md` | plan (and wait) → spec → plan → tasks → implementation → tests → review → ADR → defend |
| `.claude/workflows/git-workflow.md` | `main`/`develop`, branch naming, Conventional Commits, small atomic commits |
| `.claude/workflows/architecture-decision.md` | when an ADR is needed and how to write one together |
