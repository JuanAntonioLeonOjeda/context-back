"""PostgreSQL side of story linking: the pairs of story centroids and the stored tree runs."""

from sqlalchemy import Engine, text

from datos.stories.domain.tree import StoryLink, StoryPair, StoryStart, TreeSettings

_LATEST_STORY_RUN = text("SELECT id FROM story_runs ORDER BY created_at DESC, id DESC LIMIT 1")
# A story's centroid is the mean of its articles' vectors (pgvector `avg`) and its start the time of
# its first article. Only stories of the run, and only vectors of the run's encoder version, so the
# cosine is between vectors of the same encoder. The window bounds the join, as in the grouping.
_PAIRS = text(
    """
    WITH centroids AS (
        SELECT sa.story_id, avg(e.embedding) AS centroid, min(a.published_at) AS started_at
        FROM story_runs r
        JOIN story_articles sa ON sa.run_id = r.id
        JOIN article_embeddings e
          ON e.article_id = sa.article_id AND e.encoder_version = r.encoder_version
        JOIN articles a ON a.id = sa.article_id
        WHERE r.id = :story_run_id
        GROUP BY sa.story_id
    )
    SELECT x.story_id AS first_id, x.started_at AS first_started_at,
           y.story_id AS second_id, y.started_at AS second_started_at,
           1 - (x.centroid <=> y.centroid) AS similarity
    FROM centroids x
    JOIN centroids y ON y.story_id > x.story_id
    WHERE abs(extract(epoch FROM x.started_at - y.started_at)) <= :window_seconds
      AND 1 - (x.centroid <=> y.centroid) >= :threshold
    """
)
_INSERT_RUN = text(
    "INSERT INTO story_tree_runs (story_run_id, threshold, window_days)"
    " VALUES (:story_run_id, :threshold, :window_days) RETURNING id"
)
_INSERT_LINK = text(
    "INSERT INTO story_links (tree_run_id, story_run_id, story_id, parent_story_id, similarity)"
    " VALUES (:tree_run_id, :story_run_id, :story_id, :parent_story_id, :similarity)"
)


class PgStoryLinkRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def latest_story_run_id(self) -> int | None:
        with self._engine.connect() as connection:
            run_id = connection.execute(_LATEST_STORY_RUN).scalar()
            return None if run_id is None else int(run_id)

    def story_pairs(self, story_run_id: int, settings: TreeSettings) -> list[StoryPair]:
        parameters = {
            "story_run_id": story_run_id,
            "window_seconds": settings.window_days * 86400,
            "threshold": settings.threshold,
        }
        with self._engine.connect() as connection:
            rows = connection.execute(_PAIRS, parameters)
            return [
                StoryPair(
                    StoryStart(r.first_id, r.first_started_at),
                    StoryStart(r.second_id, r.second_started_at),
                    float(r.similarity),
                )
                for r in rows
            ]

    def add_run(self, story_run_id: int, settings: TreeSettings, links: list[StoryLink]) -> int:
        with self._engine.begin() as connection:
            tree_run_id = int(
                connection.execute(
                    _INSERT_RUN,
                    {
                        "story_run_id": story_run_id,
                        "threshold": settings.threshold,
                        "window_days": settings.window_days,
                    },
                ).scalar_one()
            )
            if links:
                connection.execute(
                    _INSERT_LINK,
                    [
                        {
                            "tree_run_id": tree_run_id,
                            "story_run_id": story_run_id,
                            "story_id": link.story_id,
                            "parent_story_id": link.parent_story_id,
                            "similarity": link.similarity,
                        }
                        for link in links
                    ],
                )
        return tree_run_id
