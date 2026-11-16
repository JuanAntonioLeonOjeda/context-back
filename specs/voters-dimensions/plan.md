# Phase 9 — voters-dimensions: plan

## 1. Domain (pure, core zone)

- `MunicipalVotes.income` becomes a generic `value` (None: no data). `Band.income_min/max` become
  `value_min/max`. The existing tests keep their cases with the new names.
- Two groupings behind one function: `EqualCensusBands` (today's `band_index` on the sorted values)
  and `FixedThresholdBands(limits)` for `size`. A dimension is data: id, name, unit, grouping.
- The vote-share rules (3 %, "Otras", candidature to party) do not change.

## 2. Education data

- Reader of the two Censo anual tables for a year, through the Tempus API with the variable filters
  that worked for the ADRH (`DATOS_METADATAOPERACION`), checked first on a small sample; the whole
  answer is measured before any load (size and time stated to the author).
- Migration `0017_municipal_values` (append-only like `municipal_income`), loader
  `python -m datos.voters load-education --year …`, repository, tests.

## 3. Read side and API

- `VotersReader.municipal_rows(territory_id, election_id, dimension, year)`: one query shape for the
  three dimensions. `community_voters(…, dimension)`.
- Route `?by=`, response models with the `dimension` block and generic ranges; OpenAPI client
  regenerated in `../front`.

## 4. Web (front, branch of its own)

- Tabs inside `VotersSection`, one panel per dimension, the existing carousel and bars. Texts per
  dimension in `es.voters.dimensions`. Fixtures captured from the backend for each dimension.

## 5. Order and risks

Domain first (renames, tests green), then education data, then the API, then the web. The risk is the
education table: its year and the exact INE category of "higher education" are verified on the real
answer before the loader is written. Age waits for its own source check.
