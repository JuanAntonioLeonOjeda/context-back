# Phase 1 — map-governments: tasks

`[core]` tasks follow the collaborative mode of `.claude/rules/ai-collaboration.md` (small
steps, explained, validated before committing). Decisions marked **author** are the
author's; ADRs are written together. Backend tasks come first; the web app starts once its
own `foundation` tasks (`front/specs/foundation/tasks.md`) are done.

## Decisions and dependencies

- [x] 1. Dependencies approved by the author: back group `geo` (`pyshp`, `shapely`, build only); front `d3-geo`
- [x] 2. ADR-0011 `[core]`: reference data decisions of `foundation` (prefixed ids, the `es` anchor, no `kind`, half-open periods, per-territory competences)
- [x] 3. Indicator definitions confirmed by the author (the table in `plan.md`)

## Governments on the map (backend)

- [x] 4. `government_in_force(terms, on_date)` `[core]`: already in `foundation` as `in_force_on`, with tests for the boundary day, before the first term and another territory
- [x] 5. `GovernmentsReader` and `TerritoryReader` ports, Postgres readers, integration tests on the real dataset
- [x] 6. Routers `/territories`, `/communities/{id}/governments`, `/parties`; 404 with a reason; tests with fake readers
- [ ] 7. Router `/map/governments` `[core]`: governing parties only, ordered by `party_id`, external support never included; a test that swaps party ids and asserts the same shape
- [x] 8. Date handling: omitted `date` means today from an injected clock; invalid dates answer 422; tests

## Geometry

- [ ] 9. Download the IGN boundaries; `data/geo/README.md` with product, date, licence and the exact attribution
- [ ] 10. `python -m datos.territories build-geometry`: 19 features keyed by territory id, simplified, attribution inside the file; tests on count, ids, validity and size
- [ ] 11. Router `/map/geometry` serving the versioned file

## Indicators

- [ ] 12. ADR-0012 `[core]`: observations append-only, indicator definitions, derived on read
- [ ] 13. Migration `0004` (`downloads`, `indicators`, `observations`, view `current_observations`); applies from scratch; constraints tested
- [ ] 14. Period rules `[core]`: `(year, period_code)` → `period_start`, rejecting unknown codes; unit tests
- [ ] 15. INE client (infrastructure) with fixtures of real responses for the five tables, including a missing value and a different scale
- [ ] 16. Loader: inserts a row only if the latest value differs; the second run adds nothing; a revised value adds one row; nothing is ever updated or deleted (test)
- [ ] 17. Derived indicator `higher_education_share_16plus` `[core]`: pure function, checks equal units, hand-computed test
- [ ] 18. Router `/communities/{id}/indicators`: latest value, period, unit, source and series; `null` for no data, never 0; real run against the INE for the 19 communities

## Web app (after the front's `foundation`)

- [ ] 19. Party colour palette `[core]` (**author**): values, contrast and colour-blindness checks, stripe pattern for pairs that look alike
- [ ] 20. ADR-0013 (front) `[core]`: SVG map with `d3-geo` and the colour encoding
- [ ] 21. Map component: projection, Canary Islands inset, markers for Ceuta and Melilla, legend, selection by mouse, touch and keyboard, text alternatives
- [ ] 22. Community card: president, governing parties, external support, caretaker note, term start, indicators with period and source links; wording without evaluation
- [ ] 23. Tests with Testing Library and axe in both themes; empty and error states

## Close

- [ ] 24. `data/` READMEs, `AGENTS.md` statuses (both repos) and OpenAPI client regenerated
- [ ] 25. Reviews: `py-reviewer`, `neutrality-reviewer`; in the front `ts-reviewer` and `accessibility-reviewer`
- [ ] 26. `/defend map-governments`; PR into `develop` with `/create-pr`

## Defend

_Date, result and gaps of `/defend map-governments`._
