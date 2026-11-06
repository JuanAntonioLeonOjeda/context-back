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

- [x] 14. Training sample of 400 (disjoint from the test set, with a test), Label Studio project with no proposals
  - Done 2026-10-21 (`train-sample-v1`, 400, seed 20261021) and 2026-10-23 (`train-sample-v2`, 100, seed 2, drawn after the learning curve), both in `data/train/`.
  - Prepared 2026-10-14: the sampler (`python -m datos.classification sample`, `data/sampling/README.md`), the enrichment terms, the Label Studio interface (`data/labelling/label-studio.xml`) and the test that the sets share no article. A dry run on 2026-10-14 found five outlets short of enriched articles (3Cat, RTVE, Telemadrid, El Confidencial, Diario de Avisos): check again before drawing on 2026-10-21.
- [x] 15. Author labels in sessions of 100; export to `data/train/train-set-v1.jsonl`
  - Done 2026-10-23: v1 (400) and v2 (100) labelled. v2 applied the strict level rule of the guide, v1 had not: the levels of v1 were re-read (`train-set-v1-revised.jsonl`, 205 changes listed in `.changes.csv`) and both were merged into `data/train/train-set-v3.jsonl` (500 articles, 25 unsure), the set the model is trained on.
- [x] 16. ADR-0016 `[core]`: encoder (licence and Catalan verified), what the model labels, promotion criteria set by the **author** before training
  - Drafted 2026-10-14 with the author's decisions (encoder mpnet-base with MiniLM as fallback, sectors and levels, training sample on 2026-10-21, promotion criteria, `ml` group approved): `docs/adr/0016-own-classifier-model.md`, accepted by the author on 2026-10-15.
- [x] 17. `ml` dependency group approved; `SetFitClassifier` adapter and training job with fixed seeds; weights in `models/`
  - Done 2026-10-15 (code): the `ml` group, `SetFitClassifier` and the composite classifier, scores stored with each classification (migration 0006), `train` (plan, `--dry-run`, frozen model directory, model card) and `learning-curve` (D11, D12: 4 folds, 2 run, subsets of 100, 200 and 300, resumable), with `scripts/train-model.sh` and `scripts/learning-curve.sh`. The real weights in `models/` and the real curve wait for the labels of task 15 (sample drawn on 2026-10-21); the model is promoted or not by task 18.
- [x] 18. Evaluation of rules and model on the test set, overall and per outlet; promotion per label
  - Done 2026-10-15 (code): `evaluate --model DIR` (bootstrap intervals, the two criteria of ADR-0016 per family, a new report per run in `data/eval/reports/`; the per-party criterion was dropped with the attribution, ADR-0018). The real evaluation waits for the trained model and the labelled blind test set (early November).
  - Run 2026-10-26 (PR #25, `data/eval/reports/20261026T123915+0000-d33978f5b50f.json`): model `d33978f5b50f` (trained on `train-set-v3`, 1 h 39 min), blind test set of 200 (seed 20261024). **Sector: promoted** (rules 0.524, model 0.584, +6.0 points; interval -5.6 to +22.2 crosses zero). **Level: stays with the rules** (0.403 vs 0.308, -9.5 points; abc and canarias7 worse). The learning curve on `train-set-v3` (2 folds) was noisy: the per-label detail showed few `state` and `local` positives, which explains level. The curve is not a promotion test.

## Change of course (2026-10-15)

- [x] 22. ADR-0018: no responsible party per news item (supersedes ADR-0005 and ADR-0014); the attribution leaves the API, the web and the code; levels stay for phase 7; competences stay as data
  - Back: the news API names no party, the `attribution` module and the competences reader removed. Front: the news card shows outlet, time, headline and link; the texts no longer describe a responsible party. Tasks 1, 3 and 10 above describe what was built before.

## Close


- [x] 19. Data READMEs, `AGENTS.md` statuses (both repos), OpenAPI client regenerated
  - Done 2026-10-14: coverage of `data/classification/README.md` recomputed for rules `d74a59205b94`; code maps of both repos completed; the OpenAPI client regenerated and found in sync. ADR-0014 and ADR-0015 were accepted by the author on 2026-10-14.
- [x] 20. Reviews: `py-reviewer`, `neutrality-reviewer`, `ts-reviewer`, `accessibility-reviewer`
  - Done 2026-10-14: `specs/news-live/review.md`. No critical finding; four warnings fixed (one connection per request, the news query by window, focus under the sticky header, a hand-typed number of outlets).
- [x] 21. PRs into `develop` (`/defend news-live` optional)

## Left for the next phase

- Wiring the promoted model into the live classification (decided 2026-10-26 to leave it out of this phase, to see the MVP first): `classify-new` still uses only the rules and the API reads `active_classifier_id = rules`. ADR-0016 leaves open where the model classifies ("not decided yet"); the `ml` group never goes in the API image.
- Retrain with all the sectors when they are added (the labels, the level rule and the test set will be redone).

## Defend (optional)

_Date, result and gaps of `/defend news-live`, if run._
