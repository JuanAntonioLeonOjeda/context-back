"""Use case: the news related to one news item, a chain back in time (spec related-news).

Each step asks the reader for the earlier candidates of the last item of the chain and lets the
domain (`domain/related.py`) choose the next one. The chain ends when no candidate qualifies or
the next one would make it cover too many days. It always ends: every step is earlier than the
one before it, and there are finitely many articles.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol
from zoneinfo import ZoneInfo

from datos.stories.domain.related import (
    Candidate,
    ChainLink,
    NewsItem,
    RelatedDay,
    RelatedSettings,
    fits,
    group_by_day,
    pick_next,
)

# The days are the readers' days: the site is about Spain.
SPAIN = ZoneInfo("Europe/Madrid")


class RelatedReader(Protocol):
    def news_item(self, article_id: int) -> NewsItem | None:
        """The news item, or None when there is no article with that id."""
        ...

    def candidates(
        self, step_id: int, origin_id: int, settings: RelatedSettings, *, limit: int = 50
    ) -> list[Candidate]:
        """The earlier candidates of a step, most similar first."""
        ...


@dataclass(frozen=True, slots=True)
class RelatedNews:
    item: NewsItem  # the news item asked for
    settings: RelatedSettings  # how the chain was made, said with the answer
    days: Sequence[RelatedDay] = field(default_factory=list)  # the chain by day, newest first

    @property
    def has_related(self) -> bool:
        """Whether anything was found besides the news item asked for."""
        return sum(len(day.links) for day in self.days) > 1


def related_news(
    reader: RelatedReader, article_id: int, settings: RelatedSettings | None = None
) -> RelatedNews | None:
    """The related news of an article, or None when the article does not exist."""
    settings = settings or RelatedSettings()
    origin = reader.news_item(article_id)
    if origin is None:
        return None
    chain = [ChainLink(origin, None)]
    while True:
        step = chain[-1].item
        candidates = reader.candidates(step.article_id, origin.article_id, settings)
        chosen = pick_next(candidates, chain, settings)
        # A candidate that does not fit is on a ninth day; any later step would be earlier still.
        if chosen is None or not fits(chain, chosen, settings, SPAIN):
            break
        chain.append(ChainLink(chosen.item, chosen.similarity))
    return RelatedNews(origin, settings, group_by_day(chain, SPAIN))
