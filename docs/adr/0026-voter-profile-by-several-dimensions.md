# ADR-0026: The voter profile by several dimensions: income, size and education

- **Status:** Proposed
- **Date:** 2026-11-16 (draft; the decisions are the author's)
- **Phase:** voters-dimensions
- **Amends:** ADR-0024 (the profile was by income only; the method is the same, the parameter is
  now chosen by the reader)

## Context

ADR-0024 groups the municipalities of a community by income. The reader wants to see the same
profile by other parameters: how the municipalities with more people with higher education
voted, or the biggest against the smallest. Everything else of ADR-0024 stands: it describes
areas and never people (ecological fallacy), municipalities are never split, a group is shown
from 3 % of the valid votes and the rest is "Otras", the data is the election's year, and the
municipalities without a value are counted apart.

Four things were not decided there. The sources were checked on 2026-11-16
(`docs/sources-audit.md`, section 12):

- **Education** comes from the INE's Censo anual de población, tables 66620 (municipalities of
  500 people or more) and 66623 (50 to 499). The API refuses their volume, so the table files
  are read. 7,563 municipalities have a value for 2023.
- **Age** has no usable source yet: the INE's municipal tables 30700 and 30701 cover 153
  municipalities, and the Padrón table 33859 is huge with its latest period unconfirmed.
- **Born abroad** (table 34982) has not had its coverage checked.
- **Size** needs no source if it is measured with the census of the election's own files.

## Options considered

### How the size of a municipality is measured
- **A — Electors of the election's electoral census** (chosen). It comes from the files already
  loaded, with no new source. It is not the number of inhabitants: electors are fewer (roughly
  three quarters of the population; *not verified*, the database holds no population).
- **B — Inhabitants from the Padrón.** What a reader means by "size", but it needs another
  source, and table 33859 is large with its latest period unconfirmed.
- **C — Inhabitants from the Censo anual tables.** Already downloaded for education, but only
  for municipalities of 50 people or more: the smallest would have no size.

### How the bands of size are cut
- **A — Fixed limits** (chosen): 1,500, 8,000 and 40,000 electors, four bands. A big city stays
  alone in its band instead of filling the community's. The limits are a rounding of the cuts by
  inhabitants first proposed (2,000, 10,000 and 50,000), not a measured optimum.
- **B — Five bands of about the same census**, as income. The same logic everywhere, but the
  capital would fill a whole band, which is what size is meant to avoid.

### How the bands of education are cut
- **A — Five bands of about the same census** (chosen), as income. The share is read against the
  rest of the community, and the distribution is skewed (national median 24.6 %, from 3.4 % to
  63.9 %).
- **B — Fixed limits** (for instance 15, 25, 35 and 45 %). Comparable between communities, but
  in most of them some bands would be empty.

### Where the values of the new dimensions are stored
- **A — One generic append-only table, `municipal_values`, with the dimension as a column**
  (chosen), and a row per loaded file in `municipal_value_loads`. Income stays in
  `municipal_income`. Age or born abroad would be rows, not migrations; the cost is that the
  closed list of dimensions in the `CHECK` changes with each new one.
- **B — One table per dimension**, as income. Stricter, with no closed list, but one migration,
  one repository and one loader each.

## Decision

Option A in each question, decided by the author on 2026-11-16 (the recommendations of the
assistant, accepted as they were):

1. The size of a municipality is its electors in the election's electoral census.
2. Size is cut at 1,500, 8,000 and 40,000 electors, four bands; income and education are cut in
   five bands of about the same census.
3. Education is the percentage of people aged 15 or over with higher education (the INE's
   "Educación superior" level), of the election's year, from tables 66620 and 66623.
4. The values of a dimension that comes from a file are stored in `municipal_values`, each load
   with the name and hash of its file; income stays where it is.
5. The API is `GET /communities/{id}/voters?by=income|size|education` (income by default); the
   answer names the dimension (id, unit, source, year) and each band carries `value_min` and
   `value_max`. An unknown `by` is a 422.
6. Age and born abroad are not in this phase: their sources are not verified.

_The reasons in the author's words: not written yet; the author adds them here. The question
most worth answering: why electors and not inhabitants, knowing they are not the same?_

## Consequences

- What gets easier: a new dimension is an entry in `domain/dimensions.py`, a way to read its
  value and, if it comes from a file, a loader and rows in `municipal_values`; the profile, the
  API and the tabs do not change.
- What we accept: the size is in electors, so a reader who thinks in inhabitants has to
  translate; the limits are rounded and decided, not measured; municipalities under 50 people
  have no education value and are counted apart; the education of a year later than 2024 is not
  published yet, so an election after it has no education profile until the INE publishes it.
- What would make us revisit this: a verified source of inhabitants for every municipality (size
  by inhabitants), a source of age or of born abroad, or a measure of how often the fixed limits
  leave a band empty in the real communities.

## Verification

- The education tables checked on 2026-11-16: 7,563 municipalities with a value for 2023; Madrid
  46.3 %, Las Palmas de Gran Canaria 33.1 %, Santa Cruz de Tenerife 36.4 %
  (`docs/sources-audit.md`, section 12).
- Loaded into a scratch database and into the local one on 2026-11-16: 7,563 values, the two file
  hashes equal to those of the audit, a second run stores nothing.
- `GET /communities/{id}/voters?by=education` read on real data (Madrid 179 municipalities,
  Canarias 88, none without a value).
- The size limits are pinned by `tests/unit/voters/test_dimensions.py`; the migration rules by
  `tests/integration/test_municipal_value_constraints.py`.
