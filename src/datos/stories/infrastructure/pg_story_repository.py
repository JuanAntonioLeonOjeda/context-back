"""PostgreSQL side of story grouping: the candidate pairs and the stored runs (migration 0010)."""

from datetime import datetime

from sqlalchemy import Engine, text

from datos.stories.domain.story import CandidatePair, GroupingSettings, Story

# By coverage, not by recency: a version started a moment ago has few vectors and would group
# almost nothing; the newest breaks a tie.
_LATEST_ENCODER_VERSION = text(
    "SELECT encoder_version FROM article_embeddings"
    " GROUP BY encoder_version ORDER BY count(*) DESC, max(created_at) DESC LIMIT 1"
)
# The cosine similarity is computed here, by pgvector: `<=>` is the cosine distance. There is no
# vector index on purpose: a join of two columns cannot use one, and the window keeps it bounded.
# Each article is compared only with the articles published after it inside the window (`y` is
# later than `x`, the id breaking a tie of the same instant), so the window is a range that the
# index on `articles.published_at` can read, and each pair is met once. Written as
# `abs(x - y) <= window`, the window could not use the index and every article was compared with
# every later id of the last 60 days before the window was checked: 16 minutes on 38,399 articles
# on 2026-11-17, 2 minutes this way. The pair is returned with the smaller id first, as before.
_PAIRS = text(
    """
    SELECT least(x.id, y.id) AS article_a_id, greatest(x.id, y.id) AS article_b_id,
           CASE WHEN x.id < y.id THEN x.outlet_id ELSE y.outlet_id END AS outlet_a_id,
           CASE WHEN x.id < y.id THEN y.outlet_id ELSE x.outlet_id END AS outlet_b_id,
           1 - (a.embedding <=> b.embedding) AS similarity,
           extract(epoch FROM y.published_at - x.published_at) / 86400 AS days_apart
    FROM articles x
    JOIN article_embeddings a
      ON a.article_id = x.id AND a.encoder_version = :encoder_version
    JOIN articles y
      ON y.published_at >= x.published_at
     AND y.published_at <= x.published_at + make_interval(secs => :window_seconds)
     AND (y.published_at > x.published_at OR y.id > x.id)
     AND y.outlet_id <> x.outlet_id
    JOIN article_embeddings b
      ON b.article_id = y.id AND b.encoder_version = :encoder_version
    WHERE x.published_at >= :since
      AND 1 - (a.embedding <=> b.embedding) >= :threshold
    ORDER BY article_a_id, article_b_id
    """
)
_INSERT_RUN = text(
    "INSERT INTO story_runs (encoder_version, threshold, window_days, since)"
    " VALUES (:encoder_version, :threshold, :window_days, :since) RETURNING id"
)
_INSERT_STORY = text("INSERT INTO stories (run_id) VALUES (:run_id) RETURNING id")
_INSERT_MEMBER = text(
    "INSERT INTO story_articles (run_id, story_id, article_id, similarity)"
    " VALUES (:run_id, :story_id, :article_id, :similarity)"
)


class PgStoryRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def latest_encoder_version(self) -> str | None:
        with self._engine.connect() as connection:
            return connection.execute(_LATEST_ENCODER_VERSION).scalar()

    def candidate_pairs(
        self, encoder_version: str, *, since: datetime, settings: GroupingSettings
    ) -> list[CandidatePair]:
        parameters = {
            "encoder_version": encoder_version,
            "since": since,
            "window_seconds": settings.window_days * 86400,
            "threshold": settings.threshold,
        }
        with self._engine.connect() as connection:
            rows = connection.execute(_PAIRS, parameters)
            return [
                CandidatePair(
                    r.article_a_id,
                    r.article_b_id,
                    r.outlet_a_id,
                    r.outlet_b_id,
                    float(r.similarity),
                    float(r.days_apart),
                )
                for r in rows
            ]

    def add_run(
        self,
        encoder_version: str,
        settings: GroupingSettings,
        stories: list[Story],
        *,
        since: datetime,
    ) -> int:
        with self._engine.begin() as connection:
            run_id = int(
                connection.execute(
                    _INSERT_RUN,
                    {
                        "encoder_version": encoder_version,
                        "threshold": settings.threshold,
                        "window_days": settings.window_days,
                        "since": since,
                    },
                ).scalar_one()
            )
            for story in stories:
                story_id = connection.execute(_INSERT_STORY, {"run_id": run_id}).scalar_one()
                connection.execute(
                    _INSERT_MEMBER,
                    [
                        {
                            "run_id": run_id,
                            "story_id": story_id,
                            "article_id": member.article_id,
                            "similarity": member.link_similarity,
                        }
                        for member in story.members
                    ],
                )
        return run_id
