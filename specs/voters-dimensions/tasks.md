# Phase 9 — voters-dimensions: tasks

Tasks marked `[core]` are written one small unit at a time, explained and reviewed by the author
before the next.

- [x] 1. The author confirms the decisions of `spec.md` (dimensions, thresholds, education measure, storage, API shape, tabs)
- [x] 2. Domain: generic `value` and range, `EqualCensusBands` and `FixedThresholdBands`, hand-computed tests `[core]`
- [x] 3. Verify the Censo anual tables 66620 and 66623 on the real answer (year, category of higher education, size, time) and record it in `docs/sources-audit.md`
- [x] 4. Migration `0017_municipal_values` and its integration test `[core]`
- [x] 5. Education reader, loader and `load-education` `[core]`
- [x] 6. Reader and `community_voters` by dimension `[core]`
- [x] 7. `GET /communities/{id}/voters?by=` and the regenerated client
- [x] 8. ADR-0026 (amends ADR-0024: several dimensions): drafted with the author; the reasons in their words are still to write
- [x] 9. Front: tabs, texts, fixtures, tests (branch of its own)
- [ ] 10. Reviews, `AGENTS.md`, PRs into `develop`
- [ ] 11. Later: age (verify the INE source first) and born abroad
