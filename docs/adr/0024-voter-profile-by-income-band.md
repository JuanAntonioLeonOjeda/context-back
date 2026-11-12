# ADR-0024: The voter profile of a community, by income band

- **Status:** Proposed
- **Date:** 2026-11-09 (decisions taken by the author on 2026-11-06; to be accepted by the author)
- **Phase:** context-voters
- **Amends:** ADR-0006 (the method in detail; the CIS stays out for now)

## Context

ADR-0006 chose official municipal results crossed with INE data, plus the CIS, worded about
areas and never about people. Building it (`specs/context-voters/`) needed answers ADR-0006 did
not give: which elections, how to group municipalities, which parties to show, and what to do
when the data does not fit the plan. The sources were checked on 2026-11-06
(`docs/sources-audit.md`, section 10):

- **Results:** the Ministerio del Interior's Infoelectoral files, general elections only (regional
  ones are published by each community). The site answers a Cloudflare challenge to automated
  clients, so the file is downloaded by hand.
- **Income:** the INE's Atlas de Distribución de Renta de los Hogares, mean net income per person,
  for every municipality except those hidden by statistical secrecy.
- **The CIS:** its licence is still unverified.

## Options considered

### How municipalities are grouped
- **A — Five bands of about the same census** (chosen). Each band holds about a fifth of the
  voters, so no band is made of a few hundred tiny villages.
- **B — Five bands of the same number of municipalities.** Easier to explain, but in a community of
  many small villages a band can have almost no voters.
- **C — Thresholds of income fixed for the whole country.** Comparable across communities, but a
  community with lower incomes could have no municipality in the top band.

### What to do with a municipality bigger than a band
- **A — Never split it: it goes whole to the band where the midpoint of its census falls**
  (chosen). The bands can be uneven (Madrid: 20 · 20 · 2 · 49 · 9 % of the census), and the web
  shows each band's share so it is visible.
- **B — Fewer bands.** Less uneven, but the capital still fills one, and detail is lost where five
  bands work.
- **C — Go down to census sections.** The INE gives income by section and the Ministerio votes by
  polling station; it would solve it, at the cost of another file, matching stations to sections
  and much more work. Out of this phase.

### Which groups are shown
- **A — Parties with at least 3 % of the community's valid votes, the rest as "Otras"** (chosen).
  The same threshold for every party.
- **B — Every candidature.** Dozens of lines with almost no votes.

### How candidatures become parties
- **A — A curated table from the file's own national accumulation head** (chosen,
  `data/voters/candidature-parties.csv`): PSC, PSdeG-PSOE and PSE-EE count as PSOE; Sumar's
  regional lists as Sumar. Names and colours come from the party table, like the rest of the site.
  *Amended by the author on 2026-11-06*: a candidature with no party in the table that reaches
  3 % is shown with its acronym from the file and a neutral colour (UPN in Navarra, 15.3 % in 2023),
  instead of disappearing into "Otras".
  *Amended by the author on 2026-11-12, after the phase's reviews*: the table is by candidature
  and no longer follows the national accumulation head. The head made PSC count as PSOE although
  PSC has its own row in the party table, and the table had no single rule for coalitions (CUP-PR
  and NC-bc counted as their main party, Sumar's coalitions as Sumar, EXISTE as nothing). The
  rule now: a candidature counts as a party only when it is that party. A party of the party
  table is itself (PSC); a territorial federation counts as its party (PSdeG-PSOE, PSE-EE,
  PSN-PSOE and PSIB-PSOE as PSOE, as the governments dataset does); a coalition is never folded
  into its main party and is shown apart by its acronym when it reaches 3 % (Sumar-ECP in
  Cataluña, Sumar-Compromís in the Comunitat Valenciana, the Més lists with Sumar in the Illes
  Balears, CUP-PR, NC-bc).
- **B — The candidature names as published.** No curation, but no party colours and regional
  variants of one party apart.

### Which income year
- **A — The election's year** (chosen): it describes the municipalities as they were when they
  voted.
- **B — The latest published.** Newer, but not the place that voted.

## Decision

Option A in each question, decided by the author on 2026-11-06:

1. General elections only: July 2023 first; 29 November 2026 when the Ministerio publishes it.
2. Five bands of about the same census; a municipality is never split and goes to the band of the
   midpoint of its census, computed in integers; empty bands stay empty and are shown as such.
3. Parties from 3 % of the community's valid votes (every municipality counted, with or without
   income); a candidature that is not in the party table, by its acronym; the rest, "Otras".
4. The income of the election's year.
5. No profile for a community with fewer than two municipalities with income (Ceuta, Melilla); the
   page says why.
6. **No CIS for now**, until its licence is verified: the profile uses official results and INE
   data only.
7. Descriptive only: no correlation, no regression and no sentence about what the voters of a party
   are like. The page explains the ecological fallacy.

_The reasons in the author's words: to be written by the author before accepting this ADR._

## Consequences

- What gets easier: every number comes from two official sources, loaded with their file hash or
  download; a profile can be rebuilt from the database at any time.
- What we accept: uneven bands where a city holds much of the census; votes from abroad (CERA) are
  not in the municipal files, so profiles cover resident voters only; 77 municipalities of the 2023
  election (5,883 people of census) have no income and are counted apart.
- What would make us revisit this: a verified CIS licence (individual-level data next to the areas);
  the need to split big cities (census sections); a regional election to show.

## Verification

- Infoelectoral layout and totals checked on the July 2023 file (8,131 municipalities, 24,284,335
  votes to candidatures in files 05 and 06): `docs/sources-audit.md`, section 10.
- ADRH 2023 loaded in a scratch database on 2026-11-06 and 2026-11-09: 8,055 municipalities; the
  maximum, 30,524 euros (Pozuelo de Alarcón), matches the INE's press release.
- The uneven bands measured on 2023 for every community before deciding (Madrid, Aragón, La Rioja,
  Ceuta and Melilla are the cases): `specs/context-voters/spec.md`, decision 9.
- `GET /communities/{id}/voters` read on real data in a scratch database on 2026-11-09 (Madrid,
  Navarra, Ceuta).
