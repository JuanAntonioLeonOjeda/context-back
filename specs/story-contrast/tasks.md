# Phase 3 — story-contrast: tasks

Tasks marked `[core]` are done together, one small unit at a time (`ai-collaboration.md`).

- [x] 1. Migration `0010_stories` (embeddings, runs, stories, story_articles) and its integration test `[core]`
- [x] 2. Domain: `Story`, `GroupingSettings`, pure `grouping.py` with unit tests (same story across outlets, different story with similar words, window edges, one outlet only) `[core]`
- [x] 3. `SentenceEncoder` adapter, `embed_articles` use case, `python -m datos.stories embed`; run on the last 60 days and record the time (2026-11-06, first scheduled run: 12,428 articles embedded in about 2 minutes on MPS; grouping 29,890 vectors took about 8.5 minutes)
- [x] 4. `group_stories` use case and `python -m datos.stories group`; run, read real groups with the author, set the provisional threshold `[core]`
- [x] 5. ADR-0020 (story grouping), written with the author `[core]`
- [x] 6. Read side: `community_stories` and `GET /communities/{id}/stories`, OpenAPI client regenerated in `../front`
- [x] 7. Front: grouped stories in the community's news list (repo `../front`)
- [x] 8. Reviews (`py-reviewer`, `neutrality-reviewer`, `ts-reviewer`, `accessibility-reviewer`), `AGENTS.md` statuses, PRs into `develop` (PRs #27, #32 and #34 merged; `AGENTS.md` updated on closing, 2026-11-06; which review agents ran is not on record in the PRs)

Closed on 2026-11-06. The common summary of a story stays out of this phase (spec, out of scope; decision D10 still open).

## Defend (optional)

_Date, result and gaps of `/defend story-contrast`, if run._
