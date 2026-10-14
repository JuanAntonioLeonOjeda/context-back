"""PostgreSQL storage of classifications (append-only, ADR-0015)."""

import json
from collections.abc import Sequence

from sqlalchemy import Engine, text

from datos.classification.application.store_classifications import ArticleText
from datos.classification.domain.labels import Labels

_UNCLASSIFIED = text(
    """
    SELECT a.id, a.headline, a.lead
    FROM articles a
    WHERE NOT EXISTS (
        SELECT 1 FROM classifications c
        WHERE c.article_id = a.id AND c.model_id = :model_id AND c.model_version = :model_version
    )
    ORDER BY a.id
    LIMIT :limit
    """
)
_INSERT = text(
    """
    INSERT INTO classifications
        (article_id, model_id, model_version, communities, sectors, levels, evidence)
    VALUES (:article_id, :model_id, :model_version, :communities, :sectors, :levels,
            CAST(:evidence AS jsonb))
    ON CONFLICT (article_id, model_id, model_version) DO NOTHING
    """
)


_SECTOR_IDS = text("SELECT id FROM sectors ORDER BY id")


class PgClassificationRepository:
    """Each call is its own transaction: a batch is stored whole or not at all."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def sector_ids(self) -> frozenset[str]:
        """The sectors of the database, to validate the rules' sector terms against."""
        with self._engine.connect() as connection:
            return frozenset(connection.execute(_SECTOR_IDS).scalars())

    def unclassified(self, model_id: str, model_version: str, *, limit: int) -> list[ArticleText]:
        with self._engine.connect() as connection:
            rows = connection.execute(
                _UNCLASSIFIED,
                {"model_id": model_id, "model_version": model_version, "limit": limit},
            )
            return [ArticleText(row.id, row.headline, row.lead) for row in rows]

    def add(self, model_id: str, model_version: str, results: Sequence[tuple[int, Labels]]) -> int:
        stored = 0
        with self._engine.begin() as connection:
            for article_id, labels in results:
                outcome = connection.execute(
                    _INSERT,
                    {
                        "article_id": article_id,
                        "model_id": model_id,
                        "model_version": model_version,
                        "communities": sorted(labels.communities),
                        "sectors": sorted(labels.sectors),
                        "levels": sorted(level.value for level in labels.levels),
                        "evidence": json.dumps(
                            [{"term": e.term, "gives": e.gives} for e in labels.evidence],
                            ensure_ascii=False,
                        ),
                    },
                )
                stored += outcome.rowcount
        return stored
