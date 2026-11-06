"""PostgreSQL reader of the tree of a story (the stories API)."""

from collections.abc import Mapping, Sequence

from sqlalchemy import Connection, text

from datos.stories.application.community_stories import StoryArticle, StoryRun
from datos.stories.application.story_tree import TreeRun
from datos.stories.domain.tree import StoryLink

_LATEST_TREE_RUN = text(
    """
    SELECT t.id, t.threshold, t.window_days, t.created_at,
           r.id AS run_id, r.encoder_version, r.threshold AS run_threshold,
           r.window_days AS run_window_days, r.created_at AS run_created_at
    FROM story_tree_runs t
    JOIN story_runs r ON r.id = t.story_run_id
    ORDER BY t.created_at DESC, t.id DESC
    LIMIT 1
    """
)
_LINKS = text(
    "SELECT story_id, parent_story_id, similarity FROM story_links WHERE tree_run_id = :tree_run_id"
)
# The lead is never selected. The order inside a story never depends on the outlet's size or line.
_ARTICLES = text(
    """
    SELECT sa.story_id, a.id AS article_id, a.outlet_id, o.name AS outlet_name,
           a.headline, a.url, a.published_at
    FROM story_articles sa
    JOIN articles a ON a.id = sa.article_id
    JOIN outlets o ON o.id = a.outlet_id
    WHERE sa.run_id = :story_run_id AND sa.story_id = ANY (:story_ids)
    ORDER BY sa.story_id, a.outlet_id, a.published_at, a.id
    """
)


class PgStoryTreeReader:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def latest_tree_run(self) -> TreeRun | None:
        row = self._connection.execute(_LATEST_TREE_RUN).first()
        if row is None:
            return None
        story_run = StoryRun(
            row.run_id, row.encoder_version, row.run_threshold, row.run_window_days,
            row.run_created_at,
        )  # fmt: skip
        return TreeRun(row.id, row.threshold, row.window_days, row.created_at, story_run)

    def links(self, tree_run_id: int) -> list[StoryLink]:
        rows = self._connection.execute(_LINKS, {"tree_run_id": tree_run_id})
        return [StoryLink(r.story_id, r.parent_story_id, float(r.similarity)) for r in rows]

    def story_articles(
        self, story_run_id: int, story_ids: Sequence[int]
    ) -> Mapping[int, tuple[StoryArticle, ...]]:
        rows = self._connection.execute(
            _ARTICLES, {"story_run_id": story_run_id, "story_ids": list(story_ids)}
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
        return {story_id: tuple(items) for story_id, items in articles.items()}
