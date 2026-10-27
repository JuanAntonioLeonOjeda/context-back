# Phase 4 — history-trace: plan

## Shape

```
stories (run N) + article_embeddings ─► story centroids ─► pairs (pgvector) ─► choose parents (pure)
                                                         ─► story_tree_runs, story_links
story_links ─► GET /stories/{id}/tree ─► web page /comunidades/:id/arbol/:storyId
```

## Decisions

- **Similarity of two stories** = cosine of their centroids (the mean of their articles' vectors,
  computed by pgvector with `avg`). Cheap and explainable; the same encoder as phase 3.
- **Parent rule** (pure, `domain/tree.py`): for each story B, among the earlier stories A with
  `start(A) < start(B)`, `start(B) - start(A) <= window_days` and similarity >= threshold, the parent
  is the most similar. "Earlier" is the pair `(first article time, story id)`, so equal times
  cannot make a cycle.
- **Provisional values**: window 14 days; threshold chosen on real trees, below the grouping
  threshold (0.88) since these are related events, not the same one.
- **Known risk**: generic themes (weather, campaign) chain into big trees. Read the biggest ones
  on real data before accepting a threshold.
- **Run = immutable**, as in phase 3: `story_tree_runs` (grouping run, threshold, window) and
  `story_links` (child, parent, similarity; one row per child, so one parent by construction).
- **Tree of a story** = the connected component in the latest tree run, built in Python from
  its links (a few hundred rows).
- **News API**: `tree_story_id` on each item = the story of the article in the latest grouping
  run, if that story has a link as child or as parent in the latest tree run.
- **Web**: nested `<ul>` with CSS connectors (no chart library), horizontal; the page is a
  route of its own.
- ADR-0021 (story links: method, threshold) with the author.

## Verify first

- Distribution of centroid similarities between stories on the real data.
- That the biggest trees are one matter and not a chain of generic ones.
