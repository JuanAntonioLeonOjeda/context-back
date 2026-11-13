# Phase 8 — org-chart: tasks

Tasks marked `[core]` are written by the assistant one small unit at a time, each explained and
reviewed by the author before the next (the governments data and the schema are core zones).

- [ ] 1. ADR-0025 reviewed and decided by the author (reasons in their words) `[core]`
- [x] 2. Migration `0016_organization` (bodies, holders, competences, their sectors) and its integration test `[core]`
- [x] 3. Pure domain: `holder_on`, `executive_chart` (order, completeness), hand-computed tests `[core]`
- [x] 4. CSV readers, validation of every problem at once, loader and `python -m datos.organization load` `[core]`
- [x] 5. Data batch 1 — the State: bodies, ministers from the BOE, competences; reviewed by the author in batches
- [ ] 6. Data batch 2 — Madrid, checked against DIR3 and its government page
- [x] 7. Read side and `GET /organization`, `GET /communities/{id}/organization` `[core]`
- [x] 8. Front (branch of its own): client regenerated, routes, nested-list chart, "Ver organigrama" link, BOE attribution
- [ ] 9. Data batches 3 and 4 — Canarias and Cataluña (names given by the author, with their URL)
- [ ] 10. Reviews (`py-reviewer`, `neutrality-reviewer`, `ts-reviewer`, `accessibility-reviewer`), `AGENTS.md`, the phases table of `project-policies.md`, PRs into `develop`
- [ ] 11. After the election of 2026-11-29: the State's new ministers (close the old rows, add the new ones)

## Defend (optional)

_Date, result and gaps of `/defend org-chart`, if run._
