"""PostgreSQL storage of article embeddings (append-only, migration 0010)."""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Engine, text

from datos.stories.application.embed_articles import ArticleToEmbed

_MISSING = text(
    """
    SELECT a.id, a.headline, a.lead
    FROM articles a
    WHERE a.published_at >= :since
      AND NOT EXISTS (
        SELECT 1 FROM article_embeddings e
        WHERE e.article_id = a.id AND e.encoder_version = :encoder_version
      )
    ORDER BY a.published_at DESC, a.id DESC
    LIMIT :limit
    """
)
_INSERT = text(
    """
    INSERT INTO article_embeddings (article_id, encoder_name, encoder_version, embedding)
    VALUES (:article_id, :encoder_name, :encoder_version, CAST(:embedding AS vector))
    ON CONFLICT (article_id, encoder_version) DO NOTHING
    """
)


class PgEmbeddingRepository:
    """Each call is its own transaction: a batch is stored whole or not at all."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def missing(self, encoder_version: str, *, since: datetime, limit: int) -> list[ArticleToEmbed]:
        with self._engine.connect() as connection:
            rows = connection.execute(
                _MISSING, {"since": since, "encoder_version": encoder_version, "limit": limit}
            )
            return [ArticleToEmbed(r.id, r.headline, r.lead) for r in rows]

    def add(
        self, encoder_name: str, encoder_version: str, vectors: Sequence[tuple[int, list[float]]]
    ) -> int:
        parameters = [
            {
                "article_id": article_id,
                "encoder_name": encoder_name,
                "encoder_version": encoder_version,
                "embedding": "[" + ",".join(repr(value) for value in vector) + "]",
            }
            for article_id, vector in vectors
        ]
        if not parameters:
            return 0
        with self._engine.begin() as connection:
            result = connection.execute(_INSERT, parameters)
        return result.rowcount
