# Phase 10 — voters-age-origin: spec

## What it solves

Phase 9 (`voters-dimensions`, ADR-0026) let the reader choose the parameter of the voter profile:
income, size, education. Two parameters were left out for lack of a verified source: the age of the
people and their place of birth. Both are now in the INE's Censo anual (`docs/sources-audit.md`,
section 13). Same method, same neutrality: it describes **areas, not people**.

## Out of scope

- Municipalities of 50 to 499 inhabitants: the Censo anual has no age or place-of-birth table for
  them. They are counted apart as "without a value" (98.4 % of the population is in the 4,144
  municipalities of 500 or more).
- Anything about individuals ("how people over 70 voted").
- Nationality, sex, activity: other tables, not asked for.

## Decisions (2026-11-16, agreed with the author)

1. **Dimensions**: `age` and `born_abroad`, in addition to `income`, `size` and `education`.
2. **Coverage**: the 4,144 municipalities of 500 or more; the others have no value.
3. **Age measure**: percentage of the population of 15 or more aged **70 or more** (`De 70 a 79` +
   `De 80 a 89` + `90 y más` over `15 y más años`), from table 66620. The 65 and over cannot be
   computed: the INE's groups are ten years wide from 40.
4. **Place of birth measure**: percentage of the population of 15 or more **born abroad**
   (`Extranjero` over `Total`), from table 66621.
5. **Method**: as education: five bands of about the same census, a municipality never split,
   municipalities without a value counted apart, the election's year.
6. **Storage**: the same `municipal_value_loads` / `municipal_values`; the closed list of dimensions
   of the `CHECK` gains `age` and `born_abroad` (a new migration).
7. **API**: `?by=income|size|education|age|born_abroad`.
8. **Web**: two more tabs. The wording of each tab is proposed to the author and approved before it
   is written (core zone).

## Acceptance criteria

1. `load-age` and `load-born-abroad` read their table file in one pass and constant memory, store the
   percentage of each municipality and year with the file's name and hash, and storing again stores
   nothing.
2. A file that is not the expected table, that has no count of the year, or that has a broken row
   is refused with its name, with exit code 1 and nothing stored.
3. `?by=age` and `?by=born_abroad` give the bands, the unit `percent`, the source and the year; an
   unknown `by` is a 422 that names the five.
4. The web page shows the two tabs, with the unit and the source of each, and the note "describes
   areas, not people" in every state.
5. No sentence says what the people of a band, or the voters of a party, are like.
