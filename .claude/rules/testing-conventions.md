---
description: Testing conventions — pytest unit tests, Testcontainers integration tests, real fixtures, injected clocks, the labelled test set and what must be tested.
---

# Testing conventions

## Tools

- **pytest** with `pytest-asyncio` only where code is async. Marker `integration` for
  tests that need Docker.
- **Testcontainers** for integration tests against a real PostgreSQL with pgvector. No
  SQLite imitation of Postgres.
- Hand-written fakes for ports (`InMemoryArticleRepository`, `FixedClock`,
  `StubClassifier`). No mocking library unless a case really needs it.

## Structure and naming

- `tests/unit/<module>/test_<file>.py`, `tests/integration/<module>/test_<file>.py`.
- Test names state the behaviour in plain English:
  `test_a_parliament_names_the_community_but_not_a_level_of_government`,
  not `test_rules`.
- Fixtures: real feed items, statistics files and LLM answers captured from the sources
  and stored under `tests/fixtures/`, never invented shapes.

## What must be tested

**Always:**
- Feed parsing with real samples, including broken ones (must be dropped, not thrown).
- Classifier contract against every adapter (the same suite runs on the stub, the LLM
  adapter with recorded answers and the own model).
- Story linking: same story across outlets, different story with similar words, window
  edges.
- Indicator calculations: per-capita, constant euros, series breaks — with hand-computed
  expectations.
- Idempotent ingestion: the same item twice → one row (integration).
- Migrations apply from scratch (integration).

**Evaluation (not unit tests):** classifier and linker are evaluated on the hand-labelled
test set (`data/eval/`), reported per outlet and per party. The test set is never used
for training or prompt tuning.

## Determinism

- No network in unit tests. No real time: inject a `Clock`.
- No LLM calls in tests: recorded answers or stubs. CI never depends on an outlet, a
  statistics site or an LLM provider being up.
- Seeds fixed wherever randomness exists.

## CI

`.github/workflows/ci.yml`: install → ruff → mypy → unit tests → integration tests
(Docker available on the runner). Green CI is required to merge.
