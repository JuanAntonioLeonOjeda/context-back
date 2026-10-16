"""PostgreSQL storage of classifications (append-only, ADR-0015)."""

import json
from collections.abc import Sequence

from sqlalchemy import Engine, text

from datos.classification.application.store_classifications import ArticleText
from datos.classification.domain.labels import Labels
from datos.classification.domain.tag_stoplist import StoplistEntry
from datos.classification.infrastructure.pg_article_tags import (
    default_stoplist,
    readable_tags_by_article,
)

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
        (article_id, model_id, model_version, communities, sectors, levels, evidence, scores)
    VALUES (:article_id, :model_id, :model_version, :communities, :sectors, :levels,
            CAST(:evidence AS jsonb), CAST(:scores AS jsonb))
    ON CONFLICT (article_id, model_id, model_version) DO NOTHING
    """
)


# Active only: the model's labels, the rules and the sampling terms come from here, and a planned
# sector of the taxonomy (is_active = false) has no labels, terms or news yet.
_SECTOR_IDS = text("SELECT id FROM sectors WHERE is_active ORDER BY id")


class PgClassificationRepository:
    """Each call is its own transaction: a batch is stored whole or not at all."""

    def __init__(self, engine: Engine, stoplist: Sequence[StoplistEntry] | None = None) -> None:
        self._engine = engine
        self._stoplist = default_stoplist(stoplist)

    def sector_ids(self) -> frozenset[str]:
        """The active sectors: what the rules, the sample and the own model may label."""
        with self._engine.connect() as connection:
            return frozenset(connection.execute(_SECTOR_IDS).scalars())

    def unclassified(self, model_id: str, model_version: str, *, limit: int) -> list[ArticleText]:
        with self._engine.connect() as connection:
            rows = connection.execute(
                _UNCLASSIFIED,
                {"model_id": model_id, "model_version": model_version, "limit": limit},
            )
            articles = list(rows)
            tags = readable_tags_by_article(
                connection, [row.id for row in articles], self._stoplist
            )
            return [
                ArticleText(row.id, row.headline, row.lead, tags.get(row.id, ()))
                for row in articles
            ]

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
                        "scores": json.dumps(
                            [
                                {"label": s.label, "probability": s.probability}
                                for s in labels.scores
                            ]
                        ),
                    },
                )
                stored += outcome.rowcount
        return stored
