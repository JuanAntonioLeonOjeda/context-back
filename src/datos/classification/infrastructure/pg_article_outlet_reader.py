"""PostgreSQL reader of the outlet of articles by id, for the per-outlet evaluation only."""

from collections.abc import Collection, Mapping

from sqlalchemy import Engine, text

_OUTLETS = text("SELECT id, outlet_id FROM articles WHERE id = ANY(:ids)")


class PgArticleOutletReader:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def outlets(self, article_ids: Collection[int]) -> Mapping[int, str]:
        with self._engine.connect() as connection:
            rows = connection.execute(_OUTLETS, {"ids": list(article_ids)})
            return {r.id: r.outlet_id for r in rows}
