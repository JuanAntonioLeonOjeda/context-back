"""PostgreSQL reader of the classified news of a community and sector (the news API)."""

from datetime import datetime

from sqlalchemy import Connection, text

from datos.governments.application.published import CompetenceLevel
from datos.news.application.community_news import ClassifiedArticle

# 1. `latest`: each article's latest classification by the active classifier, so a new version
#    of the rules (or the own model) replaces the old labels without configuration.
# 2. `matching`: the community and sector asked for, inside the window, numbered per outlet.
# 3. At most `per_outlet` per outlet; the order never depends on the outlet's size or line.
# The lead is never selected: the API must not be able to return it.
_RECENT = text(
    """
    WITH latest AS (
        SELECT DISTINCT ON (c.article_id)
               c.article_id, c.communities, c.sectors, c.levels, c.model_id, c.model_version
        FROM classifications c
        WHERE c.model_id = :model_id
        ORDER BY c.article_id, c.created_at DESC, c.id DESC
    ),
    matching AS (
        SELECT a.id, a.outlet_id, o.name AS outlet_name, a.headline, a.url, a.published_at,
               l.levels, l.model_id, l.model_version,
               row_number() OVER (
                   PARTITION BY a.outlet_id ORDER BY a.published_at DESC, a.id DESC
               ) AS rank_in_outlet
        FROM latest l
        JOIN articles a ON a.id = l.article_id
        JOIN outlets o ON o.id = a.outlet_id
        WHERE :territory_id = ANY (l.communities)
          AND :sector_id = ANY (l.sectors)
          AND a.published_at >= :since
    )
    SELECT * FROM matching
    WHERE rank_in_outlet <= :per_outlet
    ORDER BY published_at DESC, outlet_id, id DESC
    """
)
_SECTOR_IDS = text("SELECT id FROM sectors")


class PgCommunityNewsReader:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def sector_ids(self) -> frozenset[str]:
        return frozenset(self._connection.execute(_SECTOR_IDS).scalars())

    def recent(
        self,
        *,
        territory_id: str,
        sector_id: str,
        since: datetime,
        model_id: str,
        per_outlet: int,
    ) -> list[ClassifiedArticle]:
        rows = self._connection.execute(
            _RECENT,
            {
                "territory_id": territory_id,
                "sector_id": sector_id,
                "since": since,
                "model_id": model_id,
                "per_outlet": per_outlet,
            },
        )
        return [
            ClassifiedArticle(
                article_id=row.id,
                outlet_id=row.outlet_id,
                outlet_name=row.outlet_name,
                headline=row.headline,
                url=row.url,
                published_at=row.published_at,
                levels=frozenset(CompetenceLevel(level) for level in row.levels),
                model_id=row.model_id,
                model_version=row.model_version,
            )
            for row in rows
        ]
