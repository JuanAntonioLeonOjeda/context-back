---
description: Project description, scope and phases, architecture summary, commands, secrets, data licences, neutrality and what not to do.
---

# Project policies and context

## What this is

A **public portfolio project**: a web portal that, for each Spanish autonomous community
(CCAA) and sector (education, health, housing first), shows the latest news from several
outlets, groups the coverage of the same story, links it to the events of the last five
years that led to it, and puts it next to official statistics, the governing party and
voter profiles. This repo is the **backend and data pipeline**; the web app lives in the
sibling repo `../front`.

Full brief: `docs/project-brief.md`. Priority: **neutrality, traceability and clarity
over features**. The working agreement with the assistant:
`.claude/rules/ai-collaboration.md`.

## Phases

Each phase goes through `.claude/workflows/spec-driven-phase.md` and has its own
`specs/<phase>/` folder and `feature/<phase>` branch.

| # | Phase (`specs/` folder) | Output |
|---|---|---|
| 0 | `foundation` | repo setup, Docker Compose with PostgreSQL, CI, ADRs 0001–0010, source audit, governments and competences dataset, 200-article blind test set |
| 1 | `map-governments` | territories, governments API, first INE indicators |
| 2 | `news-live` | RSS ingestion, classification (LLM proposes, author validates), party attribution; 2b: own classifier |
| 3 | `story-contrast` | clustering of the same story across outlets, common summary |
| 4 | `history-trace` | five-year history, links between stories |
| 5 | `context-voters` | sector indicators next to each story, voter profiles |
| 6 | `verification` | claim extraction, verdicts, review panel (from the original draft) |

**Do not start a phase without the previous one closed.** The current phase is the one
whose `specs/<phase>/tasks.md` has unchecked tasks; if none exists, it is the next one.

## Architecture in one paragraph

Ingestion adapters fetch articles (RSS now, GDELT and sitemaps for history) and store
metadata only. A classification pipeline (rules and dictionaries, embeddings, and an
`ArticleClassifier` port backed first by an LLM and later by the author's own model)
assigns CCAA, sector and government level. Attribution applies the competence table to the
government in force on the article date. A linker groups articles into stories and links
stories over time. An ETL loads official statistics and election results. PostgreSQL
(pgvector, Spanish full-text search) holds everything; FastAPI exposes it read-only to the
web app. Details: `.claude/rules/architecture.md`.

## When to use each `.claude/` mechanism (to avoid noise)

- **Rule** (`.claude/rules/`): conventions that always apply. Path-scoped rules
  (`paths:` frontmatter) only load when matching files are touched.
- **Skill** (`.claude/skills/`): non-obvious domain knowledge. None yet: the first ones
  (`news-sources`, `governments-competences`) are written in `foundation`, when there is
  something verified to record. A skill records **verified** facts; unverified ones are
  marked as such.
- **Agent** (`.claude/agents/`): repetitive review in an isolated context, read-only.
- **Command** (`.claude/commands/`): short sequence invoked by hand.
- **Workflow** (`.claude/workflows/`): multi-step process.

## Commands

From the repo root (fill in the real scripts during `foundation` and keep this list
true):

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest                      # unit tests, no network, no containers
uv run pytest -m integration       # Testcontainers: real PostgreSQL with pgvector (needs Docker)
docker compose up -d               # PostgreSQL + Label Studio
docker compose ps
```

## Secrets and configuration

- All configuration through environment variables, documented in `.env.example`. `.env`
  is never committed and never read by the assistant.
- API keys (LLM provider, any news or statistics API) live only in `.env`.

## Data licences and publishing limits

- Official statistics: respect each source's licence and show attribution in the API
  response and in the web app.
- News: **publish only headline and link** (LPI art. 129 bis). The lead is stored and
  processed internally for classification under the text-and-data-mining exception
  (RDL 24/2021 art. 67), never shown. Never store article bodies.
- Outlets with an express mining reservation are not processed. Outlets flagged
  `external_llm_allowed = false` (`data/news/outlets.csv`) are never sent to an external
  LLM. Respect `robots.txt` and never bypass bot protection. Details:
  `docs/sources-audit.md`. Legal review before any public launch.

## Neutrality is a product requirement

- Every party is treated by the same code path. No party-specific branches, colours or
  wording in code; party data comes from one table.
- The responsible party is always derived by the rule in ADR-0005, never typed by hand
  into an article, and is shown with its confidence.
- All outlets that cover a story are shown, in a stable order that does not depend on
  engagement or ranking.
- Evaluation metrics of classifiers are reported per outlet and per party.
- Texts shown to users have no evaluative adjectives about parties or governments.
- Review with the `neutrality-reviewer` agent.

## What NOT to do

- Do not implement a phase without its plan being confirmed by the author
  (`spec-driven-phase`, step 1).
- Do not generate a core zone in one go (see `ai-collaboration.md`, section 2).
- Do not let the LLM produce numbers, parties or dates that end up shown: it labels and
  summarises; facts come from the database.
- Do not call the LLM for something a rule or a lookup answers.
- Do not store or publish article bodies.
- Do not add dependencies outside the stack in ADR-0003 without justifying them first and
  getting a yes.
- Do not commit secrets, `.env`, model weights or raw downloads.
- Do not create content in `.claude/` just to fill a folder: add it when the need is real.
