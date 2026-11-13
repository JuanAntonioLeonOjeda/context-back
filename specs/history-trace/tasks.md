# Phase 4 — history-trace: tasks

- [x] 1. Migration `0011_story_links` and its constraint tests `[core]`
- [x] 2. Pure `choose_parents` with unit tests (chronology, window, threshold, ties, order) `[core]`
- [x] 3. Pairs of story centroids with pgvector; `link` job and `python -m datos.stories link`; read real trees with the author and set the provisional threshold `[core]`
- [x] 4. ADR-0021 (story links) with the author `[core]`
- [x] 5. Read side: `GET /stories/{id}/tree`; `tree_story_id` on the news items; OpenAPI client regenerated
- [x] 6. Front: "ver árbol" button on the news items and the tree page, horizontal
- [x] 7. Reviews, `AGENTS.md` statuses, PRs into `develop` (PRs #28 and #33 merged; `AGENTS.md` updated on closing, 2026-11-06; which review agents ran is not on record in the PRs)

Closed on 2026-11-06. Since then the stories are updated daily by `scripts/update-stories.sh` (PR #38).

## Defend (optional)

_Date, result and gaps of `/defend history-trace`, if run._
