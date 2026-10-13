# Phase 0 — foundation: spec

## What it solves

The project has decisions and agent configuration but no running code and no verified
data. This phase leaves a backend that starts, a database with the reference data that
every later phase needs (territories, parties, governments, competences), a verified
catalogue of sources, and the blind test set that will measure every classifier.

## Out of scope

- Classifying or linking articles (phase `news-live` and later).
- Statistical indicators beyond identifying the INE tables (phase `map-governments`).
- Election results and voter profiles (phase `context-voters`).
- Municipal governments (only state and regional levels here).
- Measuring LLM cost (phase `news-live`, on a sample).
- Public deployment.

## Acceptance criteria

**AC1 — local environment.**
Given a clean checkout with Docker and `uv` installed, when the author runs `uv sync` and
`docker compose up -d`, then PostgreSQL (with the `vector` extension available) and Label
Studio report healthy, and `GET /health` returns 200 with the database status.

**AC2 — quality gates.**
Given any commit on the branch, when CI runs, then ruff, mypy (strict), unit tests and
integration tests (real PostgreSQL in a container) pass.

**AC3 — schema.**
Given an empty database, when `alembic upgrade head` runs, then the tables for
territories, parties, government terms with their parties, and competences exist; an
integration test applies all migrations from scratch.

**AC4 — territories.**
Given the loader, when it runs twice, then the State, the 19 communities (Ceuta and
Melilla included) and the 50 provinces exist exactly once, keyed by a prefixed id (`es`, `ccaa-NN`, `prov-NN`) with the INE
code in its own column.

**AC5 — governments.** [core]
Given `data/governments/`, when the loader runs, then every government term since
2020-01-01 of the State and of the 19 regional territories exists with: president,
parties and their role (governing or external support), whether it is caretaker,
`valid_from`, `valid_to` (empty if in force)
and a source URL. Tests prove that terms of one territory do not overlap and leave no
gaps since 2020-01-01. The loader is idempotent.

**AC6 — competences.** [core]
Given the competence table for education, health and housing, when the author reviews it,
then every row has a sector, an activity, a level (state, ccaa, local), a function
(basic legislation, development legislation, execution) and a legal basis with a source;
a shared competence is one row per level; the author has approved it.

**AC7 — sources audit.**
Given the candidate outlets and data sources, when the audit is done, then
`docs/sources-audit.md` records for each: what was checked, on which date, the result
(RSS feeds per section, GDELT coverage for the pilot communities, INE table ids,
availability of election results, licence and terms notes) and a verdict. The skill
`news-sources` records only the verified facts.

**AC8 — pilot.**
Given the verified governments, when the author chooses, then two or three pilot
communities with governments of different parties (at least one coalition) are recorded
in `docs/project-brief.md`.

**AC9 — blind test set.**
Given a labelling guide and a Label Studio project, when the author labels 200 articles
from the approved outlets without seeing any model proposal, then
`data/eval/test-set-v1.jsonl` holds for each article its id, outlet, URL, `published_at`
and labels (communities, sectors or none, government level). Headlines and leads stay in
the local database, not in git.

**AC10 — decisions.**
Given ADR-0001 to ADR-0010, when the author has reviewed them, then each one states the
reasoning in the author's words and is `Accepted`.

## Open questions

None blocking. The pilot (AC8) is chosen during the phase, after the governments are
verified. The query layer is proposed in `plan.md` and needs the author's yes before
task 3.
