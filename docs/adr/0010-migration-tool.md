# ADR-0010: Alembic for database migrations

- **Status:** Accepted
- **Date:** 2026-10-13
- **Phase:** foundation

## Context

The schema will grow phase by phase (reference data, articles, embeddings, stories,
indicators). Migrations must be versioned, applied from scratch in integration tests and
never edited once merged.

## Options considered

### Option A — Alembic (chosen)
Python migration tool on top of SQLAlchemy.
- Pros: standard in Python projects; runs from the same toolchain; easy to apply in tests.
- Cons: autogeneration can hide what changes, so operations are written by hand.

### Option B — Plain SQL files with dbmate
Numbered `.sql` files applied by an external tool.
- Pros: the SQL is fully visible.
- Cons: an extra binary outside the Python toolchain.

## Decision

Alembic, with operations written by hand (no autogeneration) and forward-only migrations:
a mistake is fixed with a new migration.

## Consequences

- What gets easier: one toolchain; migrations tested from scratch in CI.
- What gets harder / what we accept: SQLAlchemy becomes a dependency even if repositories
  use little of it.
- What would make us revisit this: if hand-written operations become harder to read than
  plain SQL.

## Verification

None needed beyond the integration test that applies every migration on an empty database.
