"""PostgreSQL reader of the headline, lead and tags of articles by id, for the training job."""

from collections.abc import Collection, Mapping, Sequence

from sqlalchemy import Engine, text

from datos.classification.application.store_classifications import ArticleText
from datos.classification.domain.tag_stoplist import StoplistEntry
from datos.classification.infrastructure.pg_article_tags import (
    default_stoplist,
    readable_tags_by_article,
)

_TEXTS = text("SELECT id, headline, lead FROM articles WHERE id = ANY(:ids)")


class PgArticleTextReader:
    def __init__(self, engine: Engine, stoplist: Sequence[StoplistEntry] | None = None) -> None:
        self._engine = engine
        self._stoplist = default_stoplist(stoplist)

    def texts(self, article_ids: Collection[int]) -> Mapping[int, ArticleText]:
        """The texts of the articles that exist; an id with no article is not in the result."""
        with self._engine.connect() as connection:
            rows = connection.execute(_TEXTS, {"ids": list(article_ids)})
            articles = list(rows)
            tags = readable_tags_by_article(connection, [r.id for r in articles], self._stoplist)
            return {
                r.id: ArticleText(r.id, r.headline, r.lead, tags.get(r.id, ())) for r in articles
            }
