---
description: Naming conventions for files, types, variables, units and dates, territories, parties and database objects.
---

# Naming conventions

## Files and modules

- `snake_case.py` always. One main responsibility per file; `utils.py` or `helpers.py` is
  a smell.
- Roles in the name where useful: `*_repository.py`, `*_classifier.py`, `*_reader.py`.
- Tests next to nothing: they live in `tests/` mirroring `src/datos/`:
  `tests/unit/<module>/test_<file>.py`, `tests/integration/...`.

## Types and values

- `PascalCase` for classes and protocols, `snake_case` for functions and variables,
  `SCREAMING_SNAKE_CASE` only for true module-level constants.
- Booleans as affirmative questions: `is_coalition`, `has_majority`.
- No abbreviations a reader must guess. CCAA is fine (it is the domain term); spell the
  rest.

## Units, dates and identifiers — always explicit

- Money carries currency and basis: `spend_eur_current`, `spend_eur_constant_2024`,
  `spend_eur_per_capita`. Never `spend` alone.
- Rates carry their denominator: `teachers_per_1000_students`, `waiting_days_mean`.
- Dates say what they are: `published_at` (outlet), `fetched_at` (us), `valid_from` /
  `valid_to` (government in force). All UTC or ISO dates; never local time without zone.
- Durations carry the unit: `link_window_days`, `fetch_interval_min`.
- Territories are keyed by a prefixed id (`es`, `ccaa-13`, `prov-28`); the INE code is a
  separate column because community and province codes overlap. Never names as keys.
- Parties: a stable `party_id` (slug) from one table; display names and colours come from
  that table only.

## Database

- Tables and columns `snake_case`, tables plural (`articles`, `government_terms`).
- Primary keys `id`; foreign keys `<entity>_id`.
- Migrations: `NNNN_short_description` (zero-padded, sequential).
- Observation tables are append-only; the current value is a view or a `valid_to IS NULL`
  filter.

## API

- Paths in English `kebab-case` plural (`/stories`, `/communities/{code}/governments`).
- JSON fields `snake_case`. Dates ISO 8601.
