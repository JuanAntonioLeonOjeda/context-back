# ADR-0026: The voter profile by several dimensions: income, size, education, age and origin

- **Status:** Proposed
- **Date:** 2026-11-16 (draft; the decisions are the author's); amended 2026-11-17
- **Phase:** voters-dimensions; amended by voters-age-origin
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
- **Age** had no usable source yet _(superseded by the amendment)_: the INE's municipal tables 30700 and 30701 cover 153
  municipalities, and the Padrón table 33859 is huge with its latest period unconfirmed.
- **Born abroad** (table 34982) had not had its coverage checked _(superseded by the amendment)_.
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
   with the name and hash of its file; income stays where it is. The same file may be loaded
   once per year (migration 0018 dropped the uniqueness of the hash: a value that did not change
   is never stored again, which is what keeps a repeated load from adding rows).
5. The API is `GET /communities/{id}/voters?by=income|size|education` (income by default); the
   answer names the dimension (id, unit, source, year) and each band carries `value_min` and
   `value_max`. An unknown `by` is a 422.
6. Age and born abroad are not in this phase: their sources are not verified. _(Superseded by the
   amendment below.)_

_The reasons in the author's words: not written yet; the author adds them here. The question
most worth answering: why electors and not inhabitants, knowing they are not the same?_

## Consequences

- What gets easier: a new dimension is an entry in `domain/dimensions.py`, a way to read its
  value and, if it comes from a file, a loader and rows in `municipal_values`; the profile, the
  API and the tabs do not change.
- What we accept: a cell of the INE's tables that is not a number (`..`) in a row we use stops the
  whole load instead of being guessed (the real files have none); the size is in electors, so a reader who thinks in inhabitants has to
  translate; the limits are rounded and decided, not measured; municipalities under 50 people
  have no education value and are counted apart; the education of a year later than 2024 is not
  published yet, so an election after it has no education profile until the INE publishes it.
- Neutrality: education is read as a property of areas, never of people. The API description
  and the web's method note say that a band's shares are those of its municipalities, and that
  nothing is said about the voters of a party.
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

## Amendment 2026-11-17: age and born abroad (phase voters-age-origin)

Point 6 left age and born abroad out because their sources were unverified. They were verified on
the real files on 2026-11-16 (`docs/sources-audit.md`, section 13) and the author decided
("500 o más, 70 o más, las dos"):

7. **Age** is the percentage of people aged 15 or over who are 70 or older (70-79, 80-89 and 90
   or more), from table 66620. **Born abroad** is the percentage of people aged 15 or over born
   abroad ("Extranjero"), from table 66621. Both are of the election's year, with the same bands
   as education: five of about the same census.
8. **Coverage is the 4,144 municipalities of 500 inhabitants or more**; the 3,419 smaller ones
   have no value and are counted apart, like any municipality without one. The INE publishes
   neither table for them, and estimating would put a number in the profile that no source gives.
9. **Born abroad is the place of birth, not the nationality**: a Spanish national born abroad
   counts and a foreign national born in Spain does not. The web says so in the method note.
10. The API is `?by=income|size|education|age|born_abroad`. The loaders share one reader that a
    `TableLayout` describes (which column says what a row counts, which values are the whole and
    the part) and one use case, `load_values(dimension, …)`; a new percentage from the Censo
    anual is a layout and a line in the migration's closed list (0019), not a new reader.

_The reasons in the author's words: not written yet; the author adds them here. Questions most
worth answering: why 70 and not 65, and why 500 inhabitants if it leaves out 45 % of the
municipalities (and in Navarra 152 of 272)?_

Consequences added: a profile by age or by origin of a community of small municipalities rests
on few of them (Navarra: 120 of 272 municipalities have a value, counted on the real answer of the API on
2026-11-17), and the web says how many are left out; the table does
not say who the people born abroad are (nationality, origin), only where they were born. The
ecological fallacy applies to age and place of birth as to the rest: a band says nothing about
the elderly or the foreign-born who live in it, nor about the voters of a party.

Verification added: loaded into the local database on 2026-11-17, 4,144 values each for 2023 (age
3.7 % to 47.1 %, median 18.7 %; born abroad 0.2 % to 73.8 %, median 10.7 %); a second run stores
nothing; the sample of Canarias and Madrid computed by hand and pinned in
`tests/integration/voters/test_table_commands.py`; the layouts are pinned by
`tests/unit/voters/test_table_source.py`.
