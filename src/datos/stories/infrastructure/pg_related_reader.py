"""PostgreSQL side of the related news: one news item, and the earlier candidates of a step.

The similarities are computed here by pgvector (`<=>` is the cosine distance) on the vectors the
worker already stored: no model runs while the API answers. Which candidate becomes the next step
is decided in `domain/related.py`.
"""

from datetime import timedelta

from sqlalchemy import Engine, text

from datos.stories.domain.related import Candidate, NewsItem, RelatedSettings

# The encoder version with most vectors, as the grouping uses (pg_story_repository.py).
_ENCODER_VERSION = text(
    "SELECT encoder_version FROM article_embeddings"
    " GROUP BY encoder_version ORDER BY count(*) DESC, max(created_at) DESC LIMIT 1"
)
_ITEM = text("SELECT id, outlet_id, headline, published_at FROM articles WHERE id = :id")
# The earlier news items of a step, most similar first: published before the step and at most
# `window` before it (a range the index on `published_at` reads), at least `step_threshold` to the
# step, each with its similarity to the item the chain started from. No vector index: the window
# keeps it to a few thousand distances (about 70 ms on 38,000 articles, 2026-11-24). A step with no
# vector (an article the worker has not reached yet) has no candidates.
_CANDIDATES = text(
    """
    SELECT b.id, b.outlet_id, b.headline, b.published_at,
           1 - (s.embedding <=> eb.embedding) AS similarity,
           1 - (o.embedding <=> eb.embedding) AS to_origin
    FROM articles a
    JOIN article_embeddings s ON s.article_id = a.id AND s.encoder_version = :encoder_version
    JOIN article_embeddings o ON o.article_id = :origin_id AND o.encoder_version = :encoder_version
    JOIN articles b
      ON b.published_at < a.published_at AND b.published_at >= a.published_at - :window
    JOIN article_embeddings eb ON eb.article_id = b.id AND eb.encoder_version = :encoder_version
    WHERE a.id = :step_id
      AND 1 - (s.embedding <=> eb.embedding) >= :step_threshold
    ORDER BY s.embedding <=> eb.embedding, b.id
    LIMIT :limit
    """
)


class PgRelatedReader:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def news_item(self, article_id: int) -> NewsItem | None:
        with self._engine.connect() as connection:
            row = connection.execute(_ITEM, {"id": article_id}).one_or_none()
        return (
            None if row is None else NewsItem(row.id, row.outlet_id, row.headline, row.published_at)
        )

    def candidates(
        self, step_id: int, origin_id: int, settings: RelatedSettings, *, limit: int = 50
    ) -> list[Candidate]:
        """The earlier candidates of a step, most similar first, at most `limit`. Fifty leaves room
        for the duplicates and the items far from the origin that the domain skips."""
        with self._engine.connect() as connection:
            encoder_version = connection.execute(_ENCODER_VERSION).scalar()
            if encoder_version is None:
                return []
            rows = connection.execute(
                _CANDIDATES,
                {
                    "encoder_version": encoder_version,
                    "step_id": step_id,
                    "origin_id": origin_id,
                    "window": timedelta(days=settings.window_days),
                    "step_threshold": settings.step_threshold,
                    "limit": limit,
                },
            )
            return [
                Candidate(
                    NewsItem(r.id, r.outlet_id, r.headline, r.published_at),
                    float(r.similarity),
                    float(r.to_origin),
                )
                for r in rows
            ]
