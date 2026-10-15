"""PostgreSQL reader of the candidates for a labelling sample."""

from datetime import datetime

from sqlalchemy import Engine, text

from datos.classification.domain.sampling import Candidate

_CANDIDATES = text(
    """
    SELECT a.id, a.outlet_id, a.url, a.headline, a.lead
    FROM articles a
    WHERE a.fetched_at <= :until
    ORDER BY a.id
    """
)


class PgCandidateReader:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def candidates(self, *, until: datetime) -> list[Candidate]:
        with self._engine.connect() as connection:
            rows = connection.execute(_CANDIDATES, {"until": until})
            return [Candidate(r.id, r.outlet_id, r.url, r.headline, r.lead) for r in rows]
