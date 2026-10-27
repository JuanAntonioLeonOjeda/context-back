"""Use case: the latest news of a community and sector.

Reads the stored classifications of the active classifier. No party is attached to an item
(ADR-0018): who governs is shown apart, from the governments dataset.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Protocol

from datos.clock import SPAIN

WINDOW_DAYS = 30  # today and the 29 days before it, in Spain
PER_OUTLET = 5


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
class CommunityNews:
    territory_id: str
    sector_id: str
    since: date  # the first day of the window, in Spain
    items: tuple[ClassifiedArticle, ...]


class CommunityNewsReader(Protocol):
    def sector_ids(self) -> frozenset[str]: ...

    def recent(
        self,
        *,
        territory_id: str,
        sector_id: str,
        since: datetime,
        model_id: str,
        per_outlet: int,
    ) -> list[ClassifiedArticle]:
        """Articles published since `since` whose latest classification by `model_id` has this
        community and sector; at most `per_outlet` per outlet (the newest); newest first, ties
        by outlet id, then article id."""
        ...


def community_news(
    *,
    territory_id: str,
    sector_id: str,
    today: date,
    model_id: str,
    news: CommunityNewsReader,
) -> CommunityNews:
    since = today - timedelta(days=WINDOW_DAYS - 1)
    articles = news.recent(
        territory_id=territory_id,
        sector_id=sector_id,
        since=datetime.combine(since, time.min, tzinfo=SPAIN),
        model_id=model_id,
        per_outlet=PER_OUTLET,
    )
    return CommunityNews(territory_id, sector_id, since, tuple(articles))
