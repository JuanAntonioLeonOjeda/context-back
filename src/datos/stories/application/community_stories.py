"""Use case: the recent stories of a community, and optionally a sector.

Reads the latest grouping run and the stored classifications of the active classifier. A story
belongs to a community (and a sector) when more than half of its articles are classified there.
Nothing here ranks outlets or stories by engagement, and no party is attached (ADR-0018).
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Protocol

from datos.clock import SPAIN

WINDOW_DAYS = 30  # same window as the news: today and the 29 days before it, in Spain
MAX_STORIES = 50


@dataclass(frozen=True, slots=True)
class StoryArticle:
    """An article as a story may show it: never its lead (sources audit, section 7)."""

    article_id: int
    outlet_id: str
    outlet_name: str
    headline: str
    url: str
    published_at: datetime


@dataclass(frozen=True, slots=True)
class StoryRun:
    """How the stories were made: what makes every group traceable (spec AC3)."""

    run_id: int
    encoder_version: str
    threshold: float
    window_days: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class CommunityStory:
    story_id: int
    articles: tuple[StoryArticle, ...]  # by outlet id, then publication time, then article id


@dataclass(frozen=True, slots=True)
class CommunityStories:
    territory_id: str
    sector_id: str | None
    since: date
    run: StoryRun | None  # None until a grouping run exists
    stories: tuple[CommunityStory, ...]  # newest article first, ties by story id


class CommunityStoriesReader(Protocol):
    def sector_ids(self) -> frozenset[str]: ...

    def latest_run(self) -> StoryRun | None: ...

    def stories(
        self,
        *,
        run_id: int,
        territory_id: str,
        sector_id: str | None,
        since: datetime,
        model_id: str,
    ) -> list[CommunityStory]:
        """Stories of the run with an article published since `since`, whose community (and sector,
        when given) hold in the latest classification by `model_id` of more than half of their
        articles. Unordered; the use case orders and caps them."""
        ...


def community_stories(
    *,
    territory_id: str,
    sector_id: str | None,
    today: date,
    model_id: str,
    stories: CommunityStoriesReader,
) -> CommunityStories:
    since = today - timedelta(days=WINDOW_DAYS - 1)
    run = stories.latest_run()
    if run is None:
        return CommunityStories(territory_id, sector_id, since, None, ())
    found = stories.stories(
        run_id=run.run_id,
        territory_id=territory_id,
        sector_id=sector_id,
        since=datetime.combine(since, time.min, tzinfo=SPAIN),
        model_id=model_id,
    )
    ordered = sorted(found, key=lambda story: (-_newest(story), story.story_id))
    return CommunityStories(territory_id, sector_id, since, run, tuple(ordered[:MAX_STORIES]))


def _newest(story: CommunityStory) -> float:
    return max(article.published_at for article in story.articles).timestamp()
