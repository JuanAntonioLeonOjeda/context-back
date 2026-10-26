# Phase 3 — story-contrast: plan

## Shape

Two background jobs (never in a request handler) and a read side:

```
articles ─► embed (ml group, on the author's machine) ─► article_embeddings
article_embeddings ─► group (pure function + thin job) ─► story_runs, stories, story_articles
stories + classifications ─► GET /communities/{id}/stories ─► web
```

The encoder is the same family as the classifier (`paraphrase-multilingual-mpnet-base-v2`, 768
dimensions, ADR-0016). The `ml` group never goes in the API image, so `embed` runs where `train`
runs; the API only reads stored rows.

## Modules (`src/datos/stories/`)

| Layer | File | Role |
|---|---|---|
| domain | `grouping.py` | **pure**: given `(article_id, outlet_id, published_at, vector)` and a threshold and window, returns the stories. Cosine similarity, pairs from different outlets inside the window, connected components. No I/O. |
| domain | `story.py` | `Story`, `StoryArticle` (similarity to the story), `GroupingSettings` |
| application | `embed_articles.py` | embeds the articles of the last N days that have no vector for this encoder version |
| application | `group_stories.py` | reads vectors, calls `grouping`, writes a run |
| application | `community_stories.py` | read use case for the API |
| infrastructure | `sentence_encoder.py` | adapter over sentence-transformers (the `ml` group); text = `article_text(headline, lead, tags)` as the classifier |
| infrastructure | `pg_embedding_repository.py`, `pg_story_repository.py`, `pg_stories_reader.py` | |
| interface | `routes.py` | `GET /communities/{id}/stories` |
| entry | `__main__.py` | `python -m datos.stories embed`, `group` |

## Schema (migration `0010_stories`)

- `article_embeddings(article_id, encoder_name, encoder_version, embedding vector(768), created_at)`,
  unique `(article_id, encoder_version)`. Append-only.
- `story_runs(id, encoder_version, threshold, window_days, created_at)`.
- `stories(id, run_id)`; `story_articles(story_id, article_id, similarity)` with
  `similarity` = cosine to the story's mean vector.
- No vector index in the MVP: the job compares only articles inside the window, ~8,500 per week,
  in memory with numpy. An HNSW index is added when the volume asks for it (not now).

## Non-obvious decisions

- **Connected components, with a check.** Pairs above the threshold from different outlets inside the
  window are linked, and the components are the stories. Known risk: chaining (A~B, B~C, so A and
  C end up together though they are not alike). The first step after the job runs is to read the
  biggest stories on real data; if they chain, the fix is a second pass that cuts a component whose
  articles are not all close to its mean, a change in `grouping.py` only.
- **Minimum two outlets** per story (AC2). Two articles of the same outlet are not a contrast.
- **Community and sector by majority** of the stored classification of its articles (more than half);
  with no majority the story has no community and appears nowhere by community.
- **Run = immutable.** A new run writes new rows; the reader uses the latest run. No update, no delete.
- **Config:** `STORY_LINK_THRESHOLD` (provisional, no default until chosen on real groups),
  `STORY_WINDOW_DAYS=3`, `EMBED_WINDOW_DAYS=60`.
- **ADR-0020** (story grouping: encoder, threshold method, window, connected components) drafted
  with the author before the grouper is accepted. Core zone.

## Verify first

- Time to embed ~17,000 articles on the author's machine (estimate unverified).
- That the tags and the stoplist give the same text as the classifier's (reuse the same reader).
- How the front lists news today, to add the group without breaking the plain list.
