# ADR-0003: Backend stack: Python, FastAPI, PostgreSQL

- **Status:** Accepted
- **Date:** 2026-10-13
- **Phase:** foundation

## Context

The backend ingests news, runs classification and embeddings, loads statistics and serves a read API.

## Options considered

### Option A — Python, FastAPI, PostgreSQL with pgvector (chosen)
One language for ingestion, statistics, ML and API; one database for data, Spanish full-text search and similarity.
- Pros: Mature data and NLP ecosystem; OpenAPI generated for the web client; no separate search engine.
- Cons: Two languages in the project (Python and TypeScript).

### Option B — TypeScript (Node) everywhere
Same language as the web app.
- Pros: One language.
- Cons: Weaker data and NLP ecosystem.

### Option C — Supabase and functions
Managed Postgres plus functions.
- Pros: Fast start.
- Cons: The data pipeline lives outside it anyway.

## Decision

Python, FastAPI and PostgreSQL. The author's classifier work and the statistics pipeline are Python; pgvector and full-text search avoid a second datastore.

## Consequences

- What gets easier: one database, one language for the pipeline, typed client from OpenAPI.
- What gets harder / what we accept: pgvector tuning at scale; two languages.
- What would make us revisit this: if vector search volume outgrows Postgres

## Verification

Tooling choices that are not trade-offs (uv, ruff, mypy, pytest) are recorded in `.claude/rules/code-style.md`, not here.
