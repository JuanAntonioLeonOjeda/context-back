# Phase 5 — context-voters: tasks

Tasks marked `[core]` are written by the assistant one small unit at a time, each explained and
reviewed by the author before the next (decided 2026-11-06).

- [x] 1. Sector indicators: `indicator_id` in `data/governments/sectors.csv`, migration `0014_sector_indicator`, loader validation `[core]`
- [x] 2. `GET /sectors` (active sectors with their indicator), OpenAPI client regenerated in `../front`
- [x] 3. Migration `0015_elections` (elections, candidatures, municipal results and votes, municipal income) and its integration test `[core]`
- [x] 4. Pure parsers of the Infoelectoral files `03`, `05`, `06` with unit tests on trimmed real lines
- [x] 5. `load_election` use case, repository and `python -m datos.voters load-election`; checks (sums, known municipalities, same hash twice) `[core]`
- [x] 6. `data/voters/candidature-parties.csv` for the 2023 Congreso, with sources
- [x] 7. ADRH income loader (`python -m datos.voters load-income --year 2023`), one request for the whole country (plan, section 3)
- [x] 8. Pure income bands by census and party shares with the 3 % rule, unit tests with hand-computed cases `[core]`
- [x] 9. Profile reader and `GET /communities/{id}/voters` `[core]`
- [x] 10. ADR-0024 (voter profile method), drafted for the author (Proposed: the author writes the reasons and accepts it)
- [x] 11. Front: the sector's indicator next to the news
- [x] 12. Front: "Perfil de voto por renta" section with bars, table and method note (core zone of the front)
- [ ] 13. Reviews (`py-reviewer`, `neutrality-reviewer`, `ts-reviewer`, `accessibility-reviewer`), `AGENTS.md`, PRs into `develop`

## Defend (optional)

_Date, result and gaps of `/defend context-voters`, if run._
