# Phase 10 — voters-age-origin: plan

## 1. Generalise the loader (core zone, one unit at a time)

The education loader is three things: read a file into counts, turn counts into a percentage per
municipality, store them. Age and place of birth are the same with other columns. So:
- The reader of a table file becomes a function of a *table layout* (which column carries the
  category, which values count as part and which as total), not a module of education.
- `education_values` becomes `share_values(counts)`: part over total per municipality, with the
  same problems (repeated, missing, part above total).
- `load_education` becomes `load_values(dimension, files, …)`; `load-education` keeps working.

## 2. Data

- Migration `0019_municipal_value_dimensions`: the `CHECK` of `municipal_value_loads.dimension`
  gains `age` and `born_abroad`. Integration test.
- Commands `load-age --year Y --file 66620.csv` and `load-born-abroad --year Y --file 66621.csv`.

## 3. Read side and API

- `DimensionId.AGE` and `.BORN_ABROAD`, equal-census bands, unit `percent`; the reader gives each
  row its value by dimension; `education_source(year)` becomes `values_source(dimension, year)`.
- Source pages: the Censo anual's, as for education.

## 4. Web (branch of its own)

- Two buttons and two entries in `es.voters.dimensions` (wording approved by the author), the
  statistic label, fixtures captured from the back, tests.

## 5. Order and risks

Loader generalisation first, with the education tests green and unchanged; then the migration and
the two commands; then the API; then the web. The risk is the 170 MB file of table 66621: the
streaming reader already handles 266 MB in 3 s and 27 MB of memory.
