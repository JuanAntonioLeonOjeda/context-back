"""Use case: the latest news of a community and sector, each with who is responsible.

Reads the stored classifications of the active classifier and computes the attribution on read
(ADR-0014), so a correction of the curated governments or competences shows at once.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Protocol

from datos.attribution.application.published import AttributionEntry, attribute
from datos.clock import SPAIN
from datos.governments.application.published import (
    Competence,
    CompetenceLevel,
    CompetencesReader,
    GovernmentsReader,
    GovernmentTerm,
)

STATE_TERRITORY_ID = "es"
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
    levels: frozenset[CompetenceLevel]  # the government levels the classifier found
    model_id: str
    model_version: str


@dataclass(frozen=True, slots=True)
class NewsItem:
    article: ClassifiedArticle
    attribution: tuple[AttributionEntry, ...]


@dataclass(frozen=True, slots=True)
class CommunityNews:
    territory_id: str
    sector_id: str
    since: date  # the first day of the window, in Spain
    items: tuple[NewsItem, ...]


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
    governments: GovernmentsReader,
    competences: CompetencesReader,
) -> CommunityNews:
    since = today - timedelta(days=WINDOW_DAYS - 1)
    articles = news.recent(
        territory_id=territory_id,
        sector_id=sector_id,
        since=datetime.combine(since, time.min, tzinfo=SPAIN),
        model_id=model_id,
        per_outlet=PER_OUTLET,
    )
    terms = [*governments.terms(territory_id), *governments.terms(STATE_TERRITORY_ID)]
    table = competences.competences()
    items = tuple(
        NewsItem(a, _attribution(a, territory_id, sector_id, terms, table)) for a in articles
    )
    return CommunityNews(territory_id, sector_id, since, items)


def _attribution(
    article: ClassifiedArticle,
    territory_id: str,
    sector_id: str,
    terms: Sequence[GovernmentTerm],
    table: Sequence[Competence],
) -> tuple[AttributionEntry, ...]:
    entries = attribute(
        community_id=territory_id,
        sector_id=sector_id,
        levels=article.levels,
        # The day in Spain: a government changes on a Spanish calendar date (the BOE).
        published_on=article.published_at.astimezone(SPAIN).date(),
        terms=terms,
        competences=table,
    )
    return tuple(entries)
