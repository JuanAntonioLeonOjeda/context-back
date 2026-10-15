"""PostgreSQL reader of the classified news of a community and sector (the news API)."""

from datetime import datetime

from sqlalchemy import Connection, text

from datos.news.application.community_news import ClassifiedArticle

# 1. `in_window`: only the articles published since `since` (index on `published_at`), so the
#    work grows with the window, not with everything ever stored.
# 2. `latest`: the latest classification of each of those by the active classifier, so a new
#    version of the rules (or the own model) replaces the old labels without configuration.
#    The window is a property of the article, so filtering by it first gives the same rows. The
#    community and the sector are not: they are filtered only after the latest classification
#    is chosen, or an older one that still had them could win over the current one.
# 3. `matching`: the community and sector asked for, numbered per outlet.
# 4. At most `per_outlet` per outlet; the order never depends on the outlet's size or line.
# The lead is never selected: the API must not be able to return it.
_RECENT = text(
    """
    WITH in_window AS (
        SELECT a.id, a.outlet_id, a.headline, a.url, a.published_at
        FROM articles a
        WHERE a.published_at >= :since
    ),
    latest AS (
        SELECT DISTINCT ON (c.article_id)
               c.article_id, c.communities, c.sectors, c.model_id, c.model_version
        FROM classifications c
        JOIN in_window w ON w.id = c.article_id
        WHERE c.model_id = :model_id
        ORDER BY c.article_id, c.created_at DESC, c.id DESC
    ),
    matching AS (
        SELECT w.id, w.outlet_id, o.name AS outlet_name, w.headline, w.url, w.published_at,
               l.model_id, l.model_version,
               row_number() OVER (
                   PARTITION BY w.outlet_id ORDER BY w.published_at DESC, w.id DESC
               ) AS rank_in_outlet
        FROM latest l
        JOIN in_window w ON w.id = l.article_id
        JOIN outlets o ON o.id = w.outlet_id
        WHERE :territory_id = ANY (l.communities)
          AND :sector_id = ANY (l.sectors)
    )
    SELECT * FROM matching
    WHERE rank_in_outlet <= :per_outlet
    ORDER BY published_at DESC, outlet_id, id DESC
    """
)
# Active only: a planned sector has no news, so `?sector=` must not accept it.
_SECTOR_IDS = text("SELECT id FROM sectors WHERE is_active")


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
                model_id=row.model_id,
                model_version=row.model_version,
            )
            for row in rows
        ]
