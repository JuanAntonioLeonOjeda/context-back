# ADR-0011: Reference data model for territories, governments and competences

- **Status:** Proposed
- **Date:** 2026-10-13
- **Phase:** map-governments (decisions taken in `foundation`)

## Context

Attribution (ADR-0005) needs, for any date since 2020, who governed each territory and
which level holds each competence. The map needs the same data for today. The decisions
below were taken with the author while building the dataset in `foundation` and were
argued only in `specs/foundation/plan.md`; this ADR records them in one place.

The data has awkward cases: INE numbers communities and provinces with overlapping codes,
coalitions can also rely on external support or be caretaker, Ceuta and Melilla do not
manage education or health care, and governments change on exact dates.

## Options considered

### Territory keys
- **A — prefixed text ids** (`es`, `ccaa-13`, `prov-28`) with the INE code in its own
  column (chosen). Pros: unambiguous and readable in URLs and logs. Cons: one more column.
- **B — the INE code as key.** Cons: `01` is both Andalucía and Álava.

### Central government
- **A — a territory row `es` as an anchor** for the State's terms (chosen). Pros: national
  and regional governments share one table and one query, which attribution needs for
  state-level competences. Cons: a row that the map and the community lists must skip.
- **B — a separate table for the State.** Cons: two code paths for the same concept.

### Kind of government
- **A — derived from the parties** (chosen): coalition = two or more governing parties;
  external support = parties with that role; only `is_caretaker` is stored.
- **B — a `kind` column** (coalition, minority, caretaker…). Cons: kinds overlap (a
  coalition with external support, in caretaker mode) and would duplicate the parties
  table. Majority vs. minority needs seats and waits for election data.

### Competences
- **A — one row per level and function** (`legislation`, `basic_legislation`,
  `development_legislation`, `execution`), with optional per-territory rows that replace
  the general rows of that activity (chosen). Pros: says who does what; covers Ceuta and
  Melilla, where the State manages education and health care.
- **B — a value `shared`.** Cons: does not tell attribution who does what.

## Decision

Prefixed territory ids with the INE code apart; the `es` row as the anchor of the State's
terms; the kind of government derived from its parties, with only `is_caretaker` stored;
competences as rows per level and function, overridable per territory.

Time is modelled with half-open periods `[valid_from, valid_to)`; `valid_to` empty means in
force. A term ends on any change of president, of the parties in government or supporting
it, or of caretaker status, because attribution depends on who governed on the exact date.
Overlaps are rejected twice: in the domain before loading, and in PostgreSQL with an
exclusion constraint.

The dataset rules (term dates from the BOE, caretaker from election day or from the
president's cessation, external support = yes votes at the investiture of parties outside
government, PSOE federations as `psoe` and the PSC apart, one source per party role) live
in `data/governments/README.md`.

In the author's words, from the decisions in `foundation`: Ceuta and Melilla are treated
as autonomous communities like the others; redundancy is removed; and the State row is
kept only as an anchor because the project is about Spain.

## Consequences

- What gets easier: one query answers "who governed territory X on date D" for the State
  and every community; attribution and the map share it; every role has its source.
- What gets harder / what we accept: the `es` row must be filtered out of community lists;
  a new government event means closing a term and opening another, even for a small change.
- What would make us revisit this: municipal governments (thousands of terms and parties
  that are not in the party table), or a need to model withdrawals of support during a
  legislature.

## Verification

Verified in `foundation`: 93 terms of the State and the 19 communities since 2020 with no
gaps or overlaps (domain tests and the database constraint); every party role with a
source; the caretaker rule checked against every statute (`data/governments/README.md`).
