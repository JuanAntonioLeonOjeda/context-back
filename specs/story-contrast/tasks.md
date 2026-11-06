# Phase 3 — story-contrast: tasks

Tasks marked `[core]` are done together, one small unit at a time (`ai-collaboration.md`).

- [ ] 1. Migration `0010_stories` (embeddings, runs, stories, story_articles) and its integration test `[core]`
- [ ] 2. Domain: `Story`, `GroupingSettings`, pure `grouping.py` with unit tests (same story across outlets, different story with similar words, window edges, one outlet only) `[core]`
- [ ] 3. `SentenceEncoder` adapter, `embed_articles` use case, `python -m datos.stories embed`; run on the last 60 days and record the time
- [ ] 4. `group_stories` use case and `python -m datos.stories group`; run, read real groups with the author, set the provisional threshold `[core]`
- [ ] 5. ADR-0020 (story grouping), written with the author `[core]`
- [ ] 6. Read side: `community_stories` and `GET /communities/{id}/stories`, OpenAPI client regenerated in `../front`
- [ ] 7. Front: grouped stories in the community's news list (repo `../front`)
- [ ] 8. Reviews (`py-reviewer`, `neutrality-reviewer`, `ts-reviewer`, `accessibility-reviewer`), `AGENTS.md` statuses, PRs into `develop`

## Defend (optional)

_Date, result and gaps of `/defend story-contrast`, if run._
