# ADR-0012: Indicators as append-only observations of what the INE published

- **Status:** Proposed
- **Date:** 2026-10-13
- **Phase:** map-governments

## Context

The community card shows five statistics from the INE (population, risk of poverty or
exclusion, share of people with higher education, unemployment rate, housing price
index). Every number shown must have a source (project brief, principle 2). The INE
revises published values, publishes series in different units and scales (the education
table is in thousands of persons), and uses its own period codes (28 for a year, 19–22 for
quarters). Later phases (`context-voters`) add more indicators and need the history.

## Options considered

### Storage of values
- **A — append-only observations** (chosen): a new row whenever a downloaded value
  differs from the latest stored one for the same indicator, community and period; every
  row points to the download that produced it.
  - Pros: any number shown can be traced to a download and a series code; revisions are
    visible, never silent.
  - Cons: the current value needs a view (latest download per key).
- **B — upsert the latest value.**
  - Pros: simplest.
  - Cons: a revision erases what was shown before; no audit trail.

### Uniqueness
- A plain `UNIQUE(indicator, territory, period, value)` was rejected: a value revised A → B
  → A must be able to come back. The loader compares with the latest stored value instead.

### Derived indicators and scale
- **A — store exactly what the INE published, compute on read** (chosen): a derived
  indicator is computed by a pure function when it is read; the scale factor is stored with
  the indicator and applied on read. None of the five indicators of this phase needs a
  derivation: the share with higher education is published as such (see Verification).
- **B — store computed values.** Cons: a stored number the INE never published, and a
  formula change would leave old rows inconsistent.

## Decision

Option A for both. Observations hold what the INE published, with the series code, the
period as the INE gives it (year and period code) plus a derived `period_start`, and the
download id. Nothing is updated or deleted. Derived indicators are computed on read by pure
functions. A community without a value returns `null`, never 0. Shown text names the
measure and the period only, with no evaluative words («Tasa de paro, 2.º trimestre 2026:
14,6 %»).

Income (household income by province, ADRH) is left out: aggregating provincial means to a
community needs a method of its own, decided in `context-voters`.

## Consequences

- What gets easier: every figure has its source; revisions are visible; new indicators are
  rows in `indicators` plus a loader mapping.
- What gets harder / what we accept: a view for current values; derived values computed on
  each read (cheap at this size).
- What would make us revisit this: indicators that need deflators or series breaks
  (`context-voters`), or a volume where computing on read is slow.

## Verification

Verified on 2026-10-13 against the INE Tempus API: the five tables return one series per
community (Ceuta and Melilla included) with `Unidad` and `Escala`; `FK_Periodo` 28 is the
year and 19–22 the quarters.

Correction (2026-10-13, task 15): the education table first chosen (66104) breaks the
population down by level of education only until 2013 (old classification); only its total
continues. Table 65289 publishes the share of people aged 16 and over with higher education
(current classification, quarterly, to 2026 Q2), so the indicator takes it as published and
no derivation is needed.

Housing price index (table 80270): base **2025 = 100**, verified on 2026-10-13 because the
four quarters of 2025 average exactly 100.0. The INE methodology pages still describe the
earlier base 2015 series; the unit shown to users states the base of the table we load.
