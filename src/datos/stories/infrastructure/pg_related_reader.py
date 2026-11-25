"""PostgreSQL side of the related news: one news item, and the earlier candidates of a step.

The similarities are computed here by pgvector (`<=>` is the cosine distance) on the vectors the
worker already stored: no model runs while the API answers. Which candidate becomes the next step
is decided in `domain/related.py`.
"""

from datetime import timedelta
from typing import Any

from sqlalchemy import Connection, Row, text

from datos.stories.domain.related import Candidate, NewsItem, RelatedSettings

# The encoder version with most vectors, as the grouping uses (pg_story_repository.py).
_ENCODER_VERSION = text(
    "SELECT encoder_version FROM article_embeddings"
    " GROUP BY encoder_version ORDER BY count(*) DESC, max(created_at) DESC LIMIT 1"
)
_ITEM = text(
    "SELECT a.id, a.outlet_id, o.name AS outlet_name, a.headline, a.url, a.published_at"
    " FROM articles a JOIN outlets o ON o.id = a.outlet_id WHERE a.id = :id"
)
# The step's own vector and instant. A step with no vector (an article the worker has not reached
# yet) has no candidates. The vector comes back as text and goes into the next query as a value.
_STEP = text(
    "SELECT a.published_at, CAST(s.embedding AS text) AS embedding"
    " FROM articles a JOIN article_embeddings s"
    "   ON s.article_id = a.id AND s.encoder_version = :encoder_version"
    " WHERE a.id = :step_id"
)
# The HNSW index (migration 0020) is approximate and the window filter comes after it: with
# iterative scans it keeps reading the graph until `limit` items pass the filter, instead of
# stopping at the first `ef_search` and returning fewer. `relaxed_order` may return them slightly
# out of order, so the outer query orders them again. Both settings last until the request's
# transaction ends and only change how an HNSW index is read.
_HNSW_SETTINGS = text(
    "SELECT set_config('hnsw.iterative_scan', 'relaxed_order', true),"
    " set_config('hnsw.ef_search', '200', true)"
)
# The earlier news items of a step, most similar first: the `limit` nearest to the step's vector
# published in the window before it (from `window_start` included to the step excluded), then
# those at least `step_threshold` to the step, each with its similarity to the item the chain
# started from. The index can only answer "nearest to a fixed vector": that is why the step's
# vector is a parameter and not a join. Filtering the threshold after the limit keeps the same
# answer: the items above it are the nearest ones. Measured on 38,000 articles (2026-11-25): 8 ms
# median per step instead of 38, none of 188 candidates of 30 random articles missed.
_CANDIDATES = text(
    """
    WITH nearest AS MATERIALIZED (
        SELECT eb.article_id, eb.embedding,
               eb.embedding <=> CAST(:step_vector AS vector) AS distance
        FROM article_embeddings eb
        JOIN articles b ON b.id = eb.article_id
        WHERE eb.encoder_version = :encoder_version
          AND b.published_at < :step_at AND b.published_at >= :window_start
        ORDER BY distance
        LIMIT :limit
    )
    SELECT b.id, b.outlet_id, ob.name AS outlet_name, b.headline, b.url, b.published_at,
           1 - n.distance AS similarity,
           1 - (o.embedding <=> n.embedding) AS to_origin
    FROM nearest n
    JOIN articles b ON b.id = n.article_id
    JOIN outlets ob ON ob.id = b.outlet_id
    JOIN article_embeddings o ON o.article_id = :origin_id AND o.encoder_version = :encoder_version
    WHERE 1 - n.distance >= :step_threshold
    ORDER BY n.distance, b.id
    """
)


class PgRelatedReader:
    """Built on the request's connection, like the API's other readers."""

    def __init__(self, connection: Connection) -> None:
        self._connection = connection
        # Read once per request: a chain asks for candidates up to a dozen times, and the version
        # does not change within a request.
        self._encoder_version: str | None = None

    def news_item(self, article_id: int) -> NewsItem | None:
        row = self._connection.execute(_ITEM, {"id": article_id}).one_or_none()
        return None if row is None else _item(row)

    def candidates(
        self, step_id: int, origin_id: int, settings: RelatedSettings, *, limit: int = 50
    ) -> list[Candidate]:
        """The earlier candidates of a step, most similar first, at most `limit`. Fifty leaves room
        for the duplicates and the items far from the origin that the domain skips."""
        if self._encoder_version is None:
            self._encoder_version = self._connection.execute(_ENCODER_VERSION).scalar()
        encoder_version = self._encoder_version
        if encoder_version is None:
            return []
        step = self._connection.execute(
            _STEP, {"encoder_version": encoder_version, "step_id": step_id}
        ).one_or_none()
        if step is None:
            return []
        self._connection.execute(_HNSW_SETTINGS)
        rows = self._connection.execute(
            _CANDIDATES,
            {
                "encoder_version": encoder_version,
                "step_vector": step.embedding,
                "step_at": step.published_at,
                "window_start": step.published_at - timedelta(days=settings.window_days),
                "origin_id": origin_id,
                "step_threshold": settings.step_threshold,
                "limit": limit,
            },
        )
        return [Candidate(_item(r), float(r.similarity), float(r.to_origin)) for r in rows]


def _item(row: Row[Any]) -> NewsItem:
    return NewsItem(row.id, row.outlet_id, row.headline, row.published_at, row.outlet_name, row.url)
