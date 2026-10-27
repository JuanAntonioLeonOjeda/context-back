"""PostgreSQL reader of the stories of a community (the stories API)."""

from datetime import datetime

from sqlalchemy import Connection, text

from datos.stories.application.community_stories import CommunityStory, StoryArticle, StoryRun

_LATEST_RUN = text(
    "SELECT id, encoder_version, threshold, window_days, created_at"
    " FROM story_runs ORDER BY created_at DESC, id DESC LIMIT 1"
)
# 1. `members`: the articles of the run's stories. The lead is never selected.
# 2. `latest`: the latest classification of each by the active classifier, as in the news reader,
#    so a new version of the rules replaces the old labels without configuration.
# 3. `votes`: per story, how many of its articles are in the community (and sector). An article
#    with no classification counts in the total and in neither vote.
# 4. A story is kept when more than half of its articles agree and its newest article is in the
#    window. The order inside a story never depends on the outlet's size or line.
_STORIES = text(
    """
    WITH members AS (
        SELECT sa.story_id, a.id AS article_id, a.outlet_id, o.name AS outlet_name,
               a.headline, a.url, a.published_at
        FROM story_articles sa
        JOIN articles a ON a.id = sa.article_id
        JOIN outlets o ON o.id = a.outlet_id
        WHERE sa.run_id = :run_id
    ),
    latest AS (
        SELECT DISTINCT ON (c.article_id) c.article_id, c.communities, c.sectors
        FROM classifications c
        WHERE c.model_id = :model_id AND c.article_id IN (SELECT article_id FROM members)
        ORDER BY c.article_id, c.created_at DESC, c.id DESC
    ),
    votes AS (
        SELECT m.story_id,
               count(*) AS total,
               count(*) FILTER (WHERE :territory_id = ANY (l.communities)) AS in_community,
               count(*) FILTER (
                   WHERE CAST(:sector_id AS text) IS NULL
                      OR CAST(:sector_id AS text) = ANY (l.sectors)
               ) AS in_sector,
               max(m.published_at) AS newest
        FROM members m
        LEFT JOIN latest l ON l.article_id = m.article_id
        GROUP BY m.story_id
    )
    SELECT m.*
    FROM votes v
    JOIN members m ON m.story_id = v.story_id
    WHERE v.in_community * 2 > v.total
      AND v.in_sector * 2 > v.total
      AND v.newest >= :since
    ORDER BY m.story_id, m.outlet_id, m.published_at, m.article_id
    """
)
_SECTOR_IDS = text("SELECT id FROM sectors WHERE is_active")


class PgCommunityStoriesReader:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def sector_ids(self) -> frozenset[str]:
        return frozenset(self._connection.execute(_SECTOR_IDS).scalars())

    def latest_run(self) -> StoryRun | None:
        row = self._connection.execute(_LATEST_RUN).first()
        if row is None:
            return None
        return StoryRun(row.id, row.encoder_version, row.threshold, row.window_days, row.created_at)

    def stories(
        self,
        *,
        run_id: int,
        territory_id: str,
        sector_id: str | None,
        since: datetime,
        model_id: str,
    ) -> list[CommunityStory]:
        rows = self._connection.execute(
            _STORIES,
            {
                "run_id": run_id,
                "territory_id": territory_id,
                "sector_id": sector_id,
                "since": since,
                "model_id": model_id,
            },
        )
        articles: dict[int, list[StoryArticle]] = {}
        for row in rows:
            articles.setdefault(row.story_id, []).append(
                StoryArticle(
                    article_id=row.article_id,
                    outlet_id=row.outlet_id,
                    outlet_name=row.outlet_name,
                    headline=row.headline,
                    url=row.url,
                    published_at=row.published_at,
                )
            )
        return [CommunityStory(story_id, tuple(items)) for story_id, items in articles.items()]
