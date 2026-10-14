# Phase 2 — news-live: tasks

`[core]` tasks follow the collaborative mode of `.claude/rules/ai-collaboration.md`. Decisions
marked **author** are the author's. The model tasks (14–18) wait for the blind test set (tasks
20 and 21 of `foundation`, early November).

## Decisions

- [x] 1. ADR-0014 `[core]`: attribution computed on read, the confidence scale, D6 = A
- [x] 2. ADR-0015: the `ArticleClassifier` port, rules as data, classifications append-only

## Attribution (back)

- [x] 3. Attribution rule `[core]`: pure function with a test for each case: named and competent (high), named without competence, local, no level named (D6-A), no government on the date, a government change on the exact date, a coalition, a caretaker term, the per-territory rows of Ceuta and Melilla, external support never responsible
- [x] 4. Reader of the competences for the read side; the governments reader is reused

## Classification (back)

- [x] 5. `data/classification/`: `places.csv`, `levels.csv`, `sectors.csv` and `exclusions.csv`, in Spanish and Catalan, with their sources and conventions in `README.md`
- [x] 6. Rules classifier `[core]` behind the `ArticleClassifier` port; contract tests; cases from the labelling guide and real feed items
- [x] 7. Migration `0005` (`classifications`, append-only trigger) and its repository; integration tests
- [x] 8. `python -m datos.classification classify-new`: classifies only what the active model has not; idempotent
- [x] 9. Real run on the stored articles; counts per outlet and sector recorded (not an evaluation: the test set does not exist yet)

## News API (back)

- [x] 10. `GET /communities/{id}/news?sector=`: last 30 days, at most 5 per outlet, newest first with ties by outlet id, attribution on read, never the lead; tests and a real run
  - Real run, 2026-10-14 (rules `216d8cbc0b67`): Canarias, Madrid and Cataluña give 0 to 16 items per sector, at most 5 per outlet; most entries are not determined because the article names no government (ADR-0014, D6 = A).

## Web (front)

- [x] 11. Client regenerated; zod schema and hook for the news of a community and sector
- [x] 12. Sector selector and news list in the community card: outlet, date, headline linking out, who is responsible, why and the confidence in words; empty state; Testing Library and axe in both themes

## Collection in Docker

- [x] 13. `collector` service (collect, then classify-new, every 3 hours); verified; then the launchd agent retired (**author**'s yes)
  - Service done and verified on 2026-10-14 (`docker/collector.sh`): one real cycle read 23 feeds, stored 335 articles with 0 failures and classified them with rules `d74a59205b94`. The launchd agent was unloaded and its plist deleted on 2026-10-14, with the author's yes (option 1: one source of collection, so the outlets are not read twice); `scripts/collect-news.sh` and `scripts/launchd/` stay as a reference for a host without Docker.

## Own model (after the blind test set)

- [ ] 14. Training sample of 400 (disjoint from the test set, with a test), Label Studio project with no proposals
- [ ] 15. Author labels in sessions of 100; export to `data/train/train-set-v1.jsonl`
- [ ] 16. ADR-0016 `[core]`: encoder (licence and Catalan verified), what the model labels, promotion criteria set by the **author** before training
- [ ] 17. `ml` dependency group approved; `SetFitClassifier` adapter and training job with fixed seeds; weights in `models/`
- [ ] 18. Evaluation of rules and model on the test set, overall, per outlet and per party; promotion per label

## Close

- [x] 19. Data READMEs, `AGENTS.md` statuses (both repos), OpenAPI client regenerated
  - Done 2026-10-14: coverage of `data/classification/README.md` recomputed for rules `d74a59205b94`; code maps of both repos completed; the OpenAPI client regenerated and found in sync. ADR-0014 and ADR-0015 were accepted by the author on 2026-10-14.
- [x] 20. Reviews: `py-reviewer`, `neutrality-reviewer`, `ts-reviewer`, `accessibility-reviewer`
  - Done 2026-10-14: `specs/news-live/review.md`. No critical finding; four warnings fixed (one connection per request, the news query by window, focus under the sticky header, a hand-typed number of outlets).
- [ ] 21. PRs into `develop` (`/defend news-live` optional)

## Defend (optional)

_Date, result and gaps of `/defend news-live`, if run._
