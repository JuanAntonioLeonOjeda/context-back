# Phase 5 — context-voters: spec

## What it solves

A news item says what happened; it does not say what the place is like. This phase adds two kinds of
context, both from official sources and both descriptive:

1. **The sector's indicator next to the news**: on a community's news for a sector, the official
   figure that sector is measured by, when there is one.
2. **Voter profiles of a community**: how the municipalities of a community voted in an election,
   grouped by the income of the municipality. It describes **areas, not people**: a municipality
   with a higher mean income voting more for a party does not mean that its richer residents did
   (ecological fallacy), and the page says so.

Priority is the project's: neutrality and traceability over features.

## Out of scope

- Regional elections (not in Infoelectoral; each community publishes its own, `docs/sources-audit.md`
  section 10). General elections only.
- The CIS (licence unverified) and any survey about individuals.
- Correlations, regressions, or any sentence about what "the voters of a party" are like.
- A map of municipalities (no municipal geometry yet): tables and bars first.
- Ranking parties by anything but name, and any party colour outside the party table.

## Decisions (2026-11-06, the author)

1. **Elections**: the general election of 23 July 2023 first; the one of 29 November 2026 is loaded
   when the Ministerio del Interior publishes it.
2. **Profiles are descriptive**: municipalities grouped by income band, and the share of each party in
   each band; worded about areas, with a method note.
3. **Sector indicators as data**: a table says which indicator belongs to which sector; a sector with
   none shows nothing. Starting point: education → higher education share, housing → housing price
   index, work → unemployment rate; health and justice have none of the five indicators.
4. **No CIS** for now.
5. **Bands weighted by population**: a community's municipalities are ordered by income and cut into
   five bands of about the same number of voters (census), not the same number of municipalities.
6. **Candidatures to parties through a curated table** with its source (e.g. PSC-PSOE and PSdeG-PSOE
   to PSOE), so names and colours come from the party table; a candidature not in it counts as
   "Otras".
7. **Parties shown**: those with at least 3 % of the community's valid votes; the rest add up to
   "Otras". The same threshold for every party.
8. **Income of the election's year** (2023 for the 2023 election), not the latest published.

## Acceptance criteria

**AC1 — results loaded.** Given the Infoelectoral zip of an election downloaded by hand, when the
loader runs, then it stores the votes of each candidature in each municipality, the valid votes and
the census, with the file's name and SHA-256; running it twice stores nothing new; and the national
totals it stores match the official ones published with the file.

**AC2 — income loaded.** Given the ADRH tables, when the loader runs, then each municipality gets its
mean net income per person for a year, with the INE table and the download it came from; a
municipality without a value has no row.

**AC3 — profile.** Given a community and an election, when the profile is read, then its
municipalities are split into income bands, and for each band the API gives the number of
municipalities, the valid votes and each party's share of them; the income year and the election
are named; parties are ordered by name; a municipality without income is counted apart and said so.

**AC4 — method.** Given the profile on the web, then a note says what a band is, which income and
election years are used, and that it describes areas and not individuals.

**AC5 — sector indicator.** Given a community's news for a sector that has an indicator, then the
indicator's latest value, period and source are shown next to the news; for a sector without one,
nothing is shown and nothing is invented.

**AC6 — neutrality.** Every party goes through the same code path; colours and names come from the
party table; no text evaluates a party, an area or its voters (`neutrality-reviewer`).

## Open questions

None. The Infoelectoral layout was verified on the July 2023 file (`docs/sources-audit.md`, section 10).
