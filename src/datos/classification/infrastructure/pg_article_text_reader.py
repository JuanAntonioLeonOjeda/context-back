"""PostgreSQL reader of the headline and lead of articles by id, for the training job."""

from collections.abc import Collection, Mapping

from sqlalchemy import Engine, text

from datos.classification.application.store_classifications import ArticleText

_TEXTS = text("SELECT id, headline, lead FROM articles WHERE id = ANY(:ids)")


class PgArticleTextReader:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def texts(self, article_ids: Collection[int]) -> Mapping[int, ArticleText]:
        """The texts of the articles that exist; an id with no article is not in the result."""
        with self._engine.connect() as connection:
            rows = connection.execute(_TEXTS, {"ids": list(article_ids)})
            return {r.id: ArticleText(r.id, r.headline, r.lead) for r in rows}
