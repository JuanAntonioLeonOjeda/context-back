# Phase 5 — context-voters: plan

Spec: `spec.md` (decisions 1–8 of 2026-11-06). Every path below is new unless it says otherwise.
Core zones (`[core]`, collaborative): `src/datos/voters/`, the migrations and the repositories.

## 1. Sector indicators (AC5)

- **Data**: `data/governments/sectors.csv` gains a column `indicator_id` (empty when the sector has
  none): education → `higher_education_share_16plus`, housing → `housing_price_index`, work →
  `unemployment_rate`. It lives with the sectors because a sector is data (ADR-0007) and the
  loader already validates them; the governments loader checks that the id is a known indicator.
- **Schema**: migration `0014_sector_indicator`: `sectors.indicator_id text NULL REFERENCES
  indicators (id)`.
- **API**: `GET /sectors`: the active sectors with their name and `indicator_id`. The web app
  already reads a community's indicators (`/communities/{id}/indicators`) and shows the one whose
  id matches, with its period and source; no number is computed in the browser.

## 2. Election results (AC1) `[core]`

- **Source**: the Infoelectoral zip, downloaded by hand (Cloudflare challenge, not bypassed) into
  `data/raw/infoelectoral/` (ignored by git). Files used (layout from `FICHEROS.doc`, checked on the
  July 2023 Congreso file, `docs/sources-audit.md` section 10):
  - `03`: candidatures: code (9–14), acronym (15–64), name (65–214), national accumulation head
    (227–232).
  - `05`: municipal totals (district `99`): INE province (12–13) and municipality (14–16), census
    INE (142–149), blank (190–197), null (198–205), votes to candidatures (206–213), official flag
    (233).
  - `06`: votes per candidature and municipality (district `99`): province, municipality,
    candidature (17–22), votes (23–30).
  Fixed width, cp1252. The votes from abroad (CERA) are not in these files: profiles cover resident
  voters only, and the method note says so.
- **Schema**: migration `0015_elections`:
  - `elections` (id `congreso-2023-07`, type, date, source file name, SHA-256, loaded_at);
  - `election_candidatures` (election, code, acronym, name, national head code);
  - `municipal_results` (election, municipality INE code `prov+mun`, census, blank, null, votes to
    candidatures);
  - `municipal_candidature_votes` (election, municipality, candidature code, votes).
  One election is loaded once: a second load of the same file (same hash) writes nothing; a
  different file for the same election is an error (results are official and final).
- **Candidature → party**: `data/voters/candidature-parties.csv` (election, national head code,
  `party_id`, source). Starts from the file's own national accumulation head, so PSC, PSdeG-PSOE
  and PSE-EE map through PSOE's head. A head not in the table counts as "Otras".
  (Changed on 2026-11-12: the table is by candidature code, see decision 6 of the spec.)
- **Checks on load**: the sum of `06` per municipality equals the "votes to candidatures" of `05`
  (verified on 2023: 24,284,335 both), every municipality code exists in `territories` (provinces
  and their community come from the INE code, not from Interior's own community numbering, which
  differs: Madrid is 12 in Interior and 13 in the INE).
- **Command**: `python -m datos.voters load-election --file data/raw/infoelectoral/02202307_MUNI.zip`.

## 3. Income by municipality (AC2)

- **Source**: INE ADRH (operation 353), one table per province ("Indicadores de renta media y
  mediana"), series "Renta neta media por persona", municipal level.
  *Changed 2026-11-06, while writing it*: the Tempus client of `indicators` reads one series per
  request (8,131 requests here) and is that module's infrastructure, which `voters` may not
  import; and the provincial tables are too big for the API ("No puede mostrarse por
  restricciones de volumen", table 30824), even filtered by concept, because they carry every
  census section. `voters` gets its own small reader over the shared `datos.http` client and makes
  **one** request: `DATOS_METADATAOPERACION/353?p=12&g1=19:&g2=482:284048&date={year}0101&tip=AM`
  (variable 19 "Municipios", every value; 482:284048 "Renta neta media por persona"). For 2023 it
  answered 8,139 series in 4.6 MB after about six minutes, so that request has a 15-minute read
  timeout (`datos.http.download` gained an optional `timeout`). The INE hides some small
  municipalities' values (statistical secrecy): they have no row.
- **Schema**: in `0015`: `municipal_income` (municipality, year, euros per person, series code,
  download id). Append-only like the observations; a municipality without a value has no row.
- **Command**: `python -m datos.voters load-income --year 2023`.

## 4. Profiles (AC3, AC4) `[core]`

- **Pure domain** (`voters/domain/bands.py`): given the municipalities of a community with census
  and income, order by income and cut into 5 bands of about the same census (decision 5): a
  municipality is not split; it goes to the band where the cumulative census falls. Municipalities
  without income are counted apart. Ties in income: by INE code, so the result is deterministic.
- **Shares**: per band, each party's votes over the band's valid votes (blank + candidatures);
  parties with at least 3 % of the community's valid votes are shown, the rest add up to "Otras"
  (decision 7). Computed on read from the stored votes; nothing derived is stored.
- **API**: `GET /communities/{id}/voters?election=congreso-2023-07`: the election, the income year,
  the bands (income range, municipalities, census, valid votes, party shares ordered by party name,
  "Otras" last), the municipalities without income, and the sources.
- **ADR-0024 draft** (with the author): the profile method (bands by census, the 3 % threshold, the
  income year, what is not claimed).

## 5. Web app (`../front`)

- Sector indicator next to the news of a sector (data from `/sectors` + the indicators already
  loaded).
- Section "Perfil de voto por renta" on the community page: one row per band with the bars of each
  party (party colours from `parties.ts`, with text), a table with the same numbers for screen
  readers, and the method note. `src/features/voters/` is a core zone of the front.

## Tests

- Unit: the parsers on trimmed real lines of the 2023 files (`tests/fixtures/infoelectoral/`), the
  band cut with hand-computed cases (equal census, one big municipality, ties, missing income), the
  shares and the 3 % rule.
- Integration: migrations from scratch; load twice (idempotent); the profile query on a small
  real slice; the sum check failing on a broken file.
- Front: axe in light and dark, the table with the bars, the method note, a sector with no
  indicator showing nothing.

## Risks and what is not verified

- The ADRH municipal series is checked on one province (Albacete, 2024); 2023 and the other 51
  tables are assumed to share the shape until the loader reads them.
- Candidature heads are per election: the 2026 table will need its own rows.
- Small municipalities without income: if a community has many, its bands rest on fewer voters;
  the API says how many are left out.
