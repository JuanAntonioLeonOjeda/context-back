"""`GET /communities/{id}/news`: the latest news of a community and sector, with who is
responsible (ADR-0014). Headline, link and date only: never the lead (sources audit, section 7).
"""

from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from datos.api.provider import Provider
from datos.attribution.application.published import AttributionEntry, Confidence, Reason
from datos.clock import Clock
from datos.governments.application.published import (
    Competence,
    CompetenceFunction,
    CompetenceLevel,
    CompetencesReader,
    GovernmentsReader,
)
from datos.news.application.community_news import (
    PER_OUTLET,
    WINDOW_DAYS,
    CommunityNewsReader,
    NewsItem,
    community_news,
)
from datos.territories.routes import TerritoryReader
from datos.territories.territory import Level

DESCRIPTION = f"""
The news of the last {WINDOW_DAYS} days (today included, Spain time) that the active classifier
placed in this community and sector, at most {PER_OUTLET} per outlet (its newest).

**Order:** publication time, newest first; ties by outlet id. The order never depends on an
outlet's size, audience or line.

Each item carries its attribution, computed on read from the competence table and the
government in force on the publication date in Spain (ADR-0014): one entry per government
level the article names, or a single `not_determined` entry with its reason.
"""


class CompetenceOut(BaseModel):
    activity: str
    description: str
    function: CompetenceFunction
    legal_basis: str
    source_url: str


class AttributionOut(BaseModel):
    level: CompetenceLevel | None
    territory_id: str | None
    confidence: Confidence
    party_ids: list[str]  # alphabetical; empty unless the confidence is high
    is_caretaker: bool
    competences: list[CompetenceOut]
    reason: Reason | None


class ClassifierOut(BaseModel):
    model_id: str
    model_version: str


class NewsItemOut(BaseModel):
    outlet_id: str
    outlet_name: str
    headline: str
    url: str
    published_at: datetime
    classified_by: ClassifierOut
    attribution: list[AttributionOut]


class CommunityNewsOut(BaseModel):
    territory_id: str
    sector_id: str
    since: date
    items: list[NewsItemOut]


def build_news_router(
    *,
    news: Provider[CommunityNewsReader],
    governments: Provider[GovernmentsReader],
    competences: Provider[CompetencesReader],
    territories: Provider[TerritoryReader],
    clock: Clock,
    classifier_id: str,
) -> APIRouter:
    router = APIRouter(tags=["news"])

    @router.get(
        "/communities/{territory_id}/news",
        response_model=CommunityNewsOut,
        description=DESCRIPTION,
    )
    def community(
        territory_id: str,
        sector: Annotated[str, Query(description="A sector id: education, health or housing")],
        news_reader: Annotated[CommunityNewsReader, Depends(news)],
        governments_reader: Annotated[GovernmentsReader, Depends(governments)],
        competences_reader: Annotated[CompetencesReader, Depends(competences)],
        territory_reader: Annotated[TerritoryReader, Depends(territories)],
    ) -> CommunityNewsOut:
        if territory_id not in {t.id for t in territory_reader.by_level(Level.CCAA)}:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown community {territory_id}")
        if sector not in news_reader.sector_ids():
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"unknown sector {sector}")
        result = community_news(
            territory_id=territory_id,
            sector_id=sector,
            today=clock.today(),
            model_id=classifier_id,
            news=news_reader,
            governments=governments_reader,
            competences=competences_reader,
        )
        return CommunityNewsOut(
            territory_id=result.territory_id,
            sector_id=result.sector_id,
            since=result.since,
            items=[_item(item) for item in result.items],
        )

    return router


def _item(item: NewsItem) -> NewsItemOut:
    article = item.article
    return NewsItemOut(
        outlet_id=article.outlet_id,
        outlet_name=article.outlet_name,
        headline=article.headline,
        url=article.url,
        published_at=article.published_at,
        classified_by=ClassifierOut(model_id=article.model_id, model_version=article.model_version),
        attribution=[_attribution(entry) for entry in item.attribution],
    )


def _attribution(entry: AttributionEntry) -> AttributionOut:
    return AttributionOut(
        level=entry.level,
        territory_id=entry.territory_id,
        confidence=entry.confidence,
        party_ids=list(entry.party_ids),
        is_caretaker=entry.is_caretaker,
        competences=[_competence(c) for c in entry.competences],
        reason=entry.reason,
    )


def _competence(competence: Competence) -> CompetenceOut:
    return CompetenceOut(
        activity=competence.activity,
        description=competence.description,
        function=competence.function,
        legal_basis=competence.legal_basis,
        source_url=competence.source_url,
    )
