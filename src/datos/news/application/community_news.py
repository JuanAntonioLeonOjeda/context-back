"""Use case: the latest news of a community and sector.

Reads the stored classifications of the active classifier. No party is attached to an item
(ADR-0018): who governs is shown apart, from the governments dataset.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Protocol

from datos.clock import SPAIN

DEFAULT_DAYS = 7  # without dates: today and the 6 days before it, in Spain (the last week)
MAX_RANGE_DAYS = 31  # the longest range one request may ask for
PER_OUTLET_PER_DAY = 5


@dataclass(frozen=True, slots=True)
class ClassifiedArticle:
    """An article as the news page may show it: never its lead (sources audit, section 7)."""

    article_id: int
    outlet_id: str
    outlet_name: str
    headline: str
    url: str
    published_at: datetime
    model_id: str
    model_version: str
    # The story of the article when it has a tree of related stories (phase history-trace).
    tree_story_id: int | None = None


@dataclass(frozen=True, slots=True)
class CommunityTrees:
    territory_id: str
    sector_id: str
    items: tuple[ClassifiedArticle, ...]  # one per tree; `tree_story_id` is always set


@dataclass(frozen=True, slots=True)
class CommunityNews:
    territory_id: str
    sector_id: str
    since: date  # the first day of the range, in Spain
    until: date  # the last day of the range, in Spain
    items: tuple[ClassifiedArticle, ...]


class CommunityNewsReader(Protocol):
    def sector_ids(self) -> frozenset[str]: ...

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
        """Articles published from `since` (included) to `until` (excluded) whose latest
        classification by `model_id` has this community and sector; at most `per_outlet_per_day`
        per outlet and day in Spain (the newest); newest first, ties by outlet id, then article
        id."""
        ...

    def latest_per_tree(
        self, *, territory_id: str, sector_id: str, model_id: str
    ) -> list[ClassifiedArticle]:
        """For each tree of related stories (latest tree run) that has an article whose latest
        classification by `model_id` has this community and sector: the newest of those articles,
        whatever its day. Newest first, ties by outlet id, then article id."""
        ...


class InvalidRangeError(ValueError):
    """The dates asked for are not a range this service answers."""


def community_news(
    *,
    territory_id: str,
    sector_id: str,
    today: date,
    date_from: date | None,
    date_to: date | None,
    model_id: str,
    news: CommunityNewsReader,
) -> CommunityNews:
    """The news of a range of days in Spain: the last `DEFAULT_DAYS` ending today by default."""
    until = date_to or today
    since = date_from or until - timedelta(days=DEFAULT_DAYS - 1)
    if since > until:
        raise InvalidRangeError("the first day is after the last day")
    if (until - since).days + 1 > MAX_RANGE_DAYS:
        raise InvalidRangeError(f"a range is at most {MAX_RANGE_DAYS} days")
    articles = news.recent(
        territory_id=territory_id,
        sector_id=sector_id,
        since=datetime.combine(since, time.min, tzinfo=SPAIN),
        until=datetime.combine(until + timedelta(days=1), time.min, tzinfo=SPAIN),
        model_id=model_id,
        per_outlet_per_day=PER_OUTLET_PER_DAY,
    )
    return CommunityNews(territory_id, sector_id, since, until, tuple(articles))


def community_trees(
    *, territory_id: str, sector_id: str, model_id: str, news: CommunityNewsReader
) -> CommunityTrees:
    """The trees of related stories that reach this community and sector, each by its newest
    article there. No date filters them: a tree is as old as its stories."""
    articles = news.latest_per_tree(
        territory_id=territory_id, sector_id=sector_id, model_id=model_id
    )
    return CommunityTrees(territory_id, sector_id, tuple(articles))
