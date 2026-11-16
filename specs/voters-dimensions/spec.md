# Phase 9 — voters-dimensions: spec

## What it solves

The voter profile of a community (ADR-0024) groups municipalities by income only. This phase lets
the reader choose the parameter the municipalities are grouped by, with income as one of them: how
did the municipalities with a higher share of people with higher education vote, or the biggest
municipalities against the smallest. Same method, same neutrality: it describes **areas, not
people**, and the page says so.

## Out of scope

- Anything about individuals ("how people aged 18 to 34 voted"): official data is municipal; the CIS
  is still out (licence unverified, ADR-0024 decision 6).
- Age, in this phase: the INE's municipal indicator tables cover 153 municipalities only, and the
  full Padrón table is heavy and its latest period was not confirmed (`project-voters-dimensions`
  memory, 2026-11-16). It comes as a later dimension once a source is verified.
- Born abroad, until the coverage of INE table 34982 is checked.
- Correlations, regressions and any sentence about what the voters of a party are like.

## Decisions to confirm (2026-11-16, proposed)

1. **Dimensions of this phase**: `income` (already loaded), `education` and `size`. Agreed with the
   author on 2026-11-16 together with age, which is deferred.
2. **Method**: as ADR-0024: five bands of about the same census, ordered by the dimension, a
   municipality never split, municipalities without a value counted apart, the election's year.
   `size` is the exception: fixed thresholds, because a big city would fill a whole band.
   Thresholds: fewer than 2,000 inhabitants · 2,000 to 9,999 · 10,000 to 49,999 · 50,000 or more.
3. **Education measure**: share of people aged 15 or more with higher education (the INE's grouped
   level that holds university degrees), from the Censo anual tables 66620 (municipalities of 500
   or more) and 66623 (50 to 499). Municipalities under 50 inhabitants have no value.
4. **Storage**: `municipal_income` stays as it is (merged, append-only); a new append-only table
   `municipal_values` holds the other dimensions that come from a download. `size` needs no table:
   it is the census of the election's municipal rows.
5. **API**: `GET /communities/{id}/voters?by=income|education|size` (income by default). The answer
   names the dimension (id, name, unit, source, year) and each band carries a generic
   `value_min` / `value_max` (income in euros, education in percent, size in inhabitants).
6. **Web**: a selector (tabs) inside the voter section, income first; the same carousel of band
   cards and vertical bars for each tab, with the unit of the dimension in each card.

## Acceptance criteria

1. `?by=income` answers what it answers today, plus the dimension and the generic range fields.
2. `?by=education` groups the community's municipalities with a value by education share into five
   bands of about equal census, lists the ones without a value apart, and gives no profile when
   fewer than two have one.
3. `?by=size` uses the fixed thresholds; an empty class stays empty and is shown as such.
4. An unknown `by` answers 422 with the allowed values.
5. Every band keeps its shown groups and "Otras" (3 % rule), the same for every dimension.
6. The web page switches dimension without leaving the section, says which one it is showing and in
   what unit, and keeps the table and the method note for each.
7. Each figure carries its source and year (INE table, download hash) as income does.
8. No sentence says what the voters of a party are like; the method note names the ecological
   fallacy for every dimension.
