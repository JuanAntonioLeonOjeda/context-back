# Phase 1 — map-governments: plan

## Decided with the author (2026-10-13)

- **Colours:** recognisable party colours, checked for contrast and colour-blindness, with
  stripes for coalitions and always a legend and labels. The palette values are chosen in
  task 19 with the author.
- **Map rendering:** own SVG with `d3-geo`, keyboard accessible, no tiles and no external
  service. Recorded in a front ADR.
- **Indicators:** the five of the spec. Income (ADRH, by province) is left out of this
  phase; it needs an aggregation method and goes to `context-voters`.
- **Order of work:** backend first (data model, API, geometry), the web app in parallel once
  its own `foundation` tasks are done.

## Verified on 2026-10-13

- **INE series by community.** The five tables return a series for each of the 19
  communities (Ceuta and Melilla included) plus the national total, and the latest values
  exist for Ceuta and Melilla. Unit and scale come with every series (`Unidad`, `Escala`):
  population in persons, AROPE in %, unemployment in %, housing index as an index, and
  the education table in **thousands of persons**.
- **Periods.** INE uses `FK_Periodo`: 28 is the year, 19–22 the four quarters. The observation
  keeps the year and the period code and derives a `period_start` date.
- **IGN boundaries.** CC BY 4.0 (Orden FOM/2807/2015). The attribution must be visible at the
  foot of the map: «Obra derivada de `<product> <date>` CC-BY 4.0 `<producer>`», with the
  product name and year taken from the selector at `scne.es/productos.html` when the file
  is downloaded. Formats: shapefile (CNIG download centre), GML (WFS and ATOM). Precision
  1:25,000, ETRS89 (REGCAN95 for the Canary Islands, compatible with WGS84).
- **Not verified:** the base year of the housing price index (expected 2015 = 100); read
  from the series metadata when the ETL is written and shown in the unit text.

## Modules

| Module | Layers | Content |
|---|---|---|
| `governments` | domain, application, infrastructure, interface | `government_in_force` (pure), `GovernmentsReader` port, Postgres reader, routers `/communities/{id}/governments` and `/map/governments` |
| `territories` | + application, interface | `TerritoryReader` port, router `/territories`, geometry build and `/map/geometry` |
| `indicators` | domain, application, infrastructure, interface | indicator definitions, `Observation`, period rules, INE client, loader, `/communities/{id}/indicators` |
| `api` | interface | wiring of routers in `create_app`; dependency injection of readers |

Only `indicators/infrastructure` talks to the INE (ETL job, never a request handler).

## API contracts (JSON, `snake_case`, ISO dates)

```
GET /territories?level=ccaa
  → [{id, ine_code, name}]                      ordered by ine_code

GET /communities/{id}/governments?date=YYYY-MM-DD       (date optional: today)
  → {territory_id, date, term: {president_name, valid_from, is_caretaker, source_url,
      parties: [{party_id, short_name, role, source_url}]}}
  404 {detail} when the id is unknown or no term covers the date

GET /map/governments?date=...
  → {date, communities: [{territory_id, is_caretaker, governing_party_ids: [...]}]}
  governing_party_ids ordered alphabetically by party_id

GET /map/geometry                                GeoJSON FeatureCollection, WGS84,
  features keyed by territory id, with `attribution` at collection level

GET /communities/{id}/indicators
  → [{indicator_id, name, unit, period, period_start, value, source, series: [{period_start, value}],
       derived_from?: [...]}]
  a community without a value for an indicator returns it with `value: null`, never 0
```

Party colours are not in the payload: they come from the `parties` table through
`GET /parties` (id, short_name, colour_hex), so the web app has one source.

## Rules worth testing as pure functions

- `government_in_force(terms, on_date)`: periods are half-open `[valid_from, valid_to)`; the
  day a term ends is the first day of the next; before the first term → `None`; exactly one
  term for any date inside the dataset (guaranteed by the data tests of `foundation`).
- Map payload: governing parties only, ordered by `party_id`; external support never.
- Period start from `(year, period_code)`: year (28), quarters (19–22); anything else is
  rejected, not guessed.
- Derived indicator `higher_education_share_16plus` = (higher education except doctorate +
  doctorate) / total, with the units of the three series checked to be equal. Computed on
  read by a pure function; the stored observations are exactly what INE published.

## Schema (migration `0004`)

```
downloads(id PK, source text, url text, fetched_at timestamptz, sha256 text)
indicators(id PK slug, name, unit, scale_factor numeric, periodicity, source_table_id text, description)
observations(id PK, indicator_id FK, territory_id FK, period_start date, period_year int,
             period_code int, value numeric, source_series_code text, download_id FK)
view current_observations: for each (indicator, territory, period_start), the row with the
                           greatest download id
```

- **Append-only** (`.claude/rules/db-migrations.md`). The loader inserts a row only when the
  latest stored value for `(indicator, territory, period_start)` differs from the downloaded
  one; a revised value is a new row, an identical one adds nothing. Uniqueness cannot be a
  plain `UNIQUE(... value)`: a value revised A → B → A must be allowed to come back.
- The scale is applied on read, so the table holds INE's numbers and a `scale_factor`, and
  the API returns values in the stated unit.
- Observations are not updated or deleted by any code path; a test asserts it.

## Indicator definitions (the author's decision; proposal)

| id | INE table | Series | Unit | Frequency |
|---|---|---|---|---|
| `population` | 56940 | «Total. Todas las edades. {community}. Población» | persons | quarterly |
| `poverty_or_exclusion_rate` | 60264 | AROPE, total | % of population | annual |
| `higher_education_share_16plus` | 66104 | derived from «Educación superior, excepto doctorado», «Doctorado» and «Total», both sexes | % of people aged 16 and over | annual |
| `unemployment_rate` | 14506 | «Tasa de paro de la población. Ambos sexos», total | % of the active population | quarterly |
| `housing_price_index` | 80270 | «General. Índice» | index (base to verify) | quarterly |

Wording shown to users names the measure and the period only («Tasa de paro, 2.º trimestre
2026: 14,6 %»), with no «high», «low» or «better than».

## Geometry pipeline

1. Download the IGN autonomous-community boundaries (shapefile) by hand once; the raw file
   goes in `data/raw/` (ignored by git), with its product name and date noted in
   `data/geo/README.md`.
2. `python -m datos.territories build-geometry` reads it, keeps the 19 communities, maps
   each to its `ccaa-NN` id by INE code, simplifies it and writes `data/geo/ccaa.geojson`
   (versioned, with the attribution).
3. A test checks 19 features, ids equal to the territories table, valid geometries and a
   size under a limit set when the file exists (target: well under 300 KB).
4. The Canary Islands inset and the markers for Ceuta and Melilla are drawn by the web app,
   so the file stays in geographic coordinates and the backend knows nothing about layout.

## Dependencies (to approve)

- Back, **build-only** group `geo`: `shapely` (coverage simplification) and its stubs
  `types-shapely`. The IGN serves GML, read with the standard library, so `pyshp` is not
  needed. Installed by default for local work and CI; not needed by the running API.
- Front (added to its own plan): `d3-geo` for the projection. Nothing else for the map.

## Configuration

`INE_BASE_URL` (default `https://servicios.ine.es/wstempus/js/ES/`). The user agent is the
shared constant. No secrets.

## ADRs of the phase

- **ADR-0011 (pending since `foundation`):** reference data decisions argued only in
  `foundation/plan.md`: prefixed territory ids, the `es` anchor, no `kind` column,
  half-open periods, per-territory competences.
- **ADR-0012:** observations and indicator definitions (append-only, derived on read).
- **ADR-0013 (front):** SVG map with `d3-geo` and the colour encoding for coalitions.

## Risks

- A coloured map reads as a verdict. Mitigation: legislature date and source on every card,
  neutral wording, legend always visible, external support never colours the map.
- Two parties with similar colours in a coalition. Mitigation: stripes plus labels; checked
  against the contrast rules in task 19.
- INE revises series. Mitigation: append-only observations with the download id.
- The state caretaker term from 2026-11-29 is missing from the data until the election.
  The map is not affected.
