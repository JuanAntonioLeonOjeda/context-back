"""PostgreSQL reader of the classified news of a community and sector (the news API)."""

from datetime import datetime

from sqlalchemy import Connection, text

from datos.news.application.community_news import ClassifiedArticle

# 1. `in_window`: only the articles published from `since` to `until` (index on `published_at`), so
#    the work grows with the range, not with everything ever stored.
# 2. `latest`: the latest classification of each of those by the active classifier, so a new
#    version of the rules (or the own model) replaces the old labels without configuration.
#    The window is a property of the article, so filtering by it first gives the same rows. The
#    community and the sector are not: they are filtered only after the latest classification
#    is chosen, or an older one that still had them could win over the current one.
# 3. `matching`: the community and sector asked for, numbered per outlet and day in Spain.
# 4. At most `per_outlet_per_day` per outlet and day; the order never depends on the outlet's size
#    or line.
# 5. `tree_story_id`: the story of the article in the grouping run the latest tree run was made
#    on, when that story has a link as child or as parent (a tree needs two stories).
# The lead is never selected: the API must not be able to return it.
_RECENT = text(
    """
    WITH in_window AS (
        SELECT a.id, a.outlet_id, a.headline, a.url, a.published_at
        FROM articles a
        WHERE a.published_at >= :since AND a.published_at < :until
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
                   PARTITION BY w.outlet_id, (w.published_at AT TIME ZONE 'Europe/Madrid')::date
                   ORDER BY w.published_at DESC, w.id DESC
               ) AS rank_in_outlet
        FROM latest l
        JOIN in_window w ON w.id = l.article_id
        JOIN outlets o ON o.id = w.outlet_id
        WHERE :territory_id = ANY (l.communities)
          AND :sector_id = ANY (l.sectors)
    )
    SELECT m.*, related.story_id AS tree_story_id
    FROM matching m
    LEFT JOIN LATERAL (
        SELECT sa.story_id
        FROM story_tree_runs t
        JOIN story_articles sa ON sa.run_id = t.story_run_id AND sa.article_id = m.id
        WHERE t.id = (SELECT id FROM story_tree_runs ORDER BY created_at DESC, id DESC LIMIT 1)
          AND EXISTS (
              SELECT 1 FROM story_links l
              WHERE l.tree_run_id = t.id
                AND sa.story_id IN (l.story_id, l.parent_story_id)
          )
    ) related ON true
    WHERE m.rank_in_outlet <= :per_outlet_per_day
    ORDER BY m.published_at DESC, m.outlet_id, m.id DESC
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
        until: datetime,
        model_id: str,
        per_outlet_per_day: int,
    ) -> list[ClassifiedArticle]:
        rows = self._connection.execute(
            _RECENT,
            {
                "territory_id": territory_id,
                "sector_id": sector_id,
                "since": since,
                "until": until,
                "model_id": model_id,
                "per_outlet_per_day": per_outlet_per_day,
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
                tree_story_id=row.tree_story_id,
            )
            for row in rows
        ]
