"""`GET /communities/{id}/news`: the latest news of a community and sector. Headline, link and
date only: never the lead (sources audit, section 7), and no party (ADR-0018).
"""

from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from datos.api.provider import Provider
from datos.clock import Clock
from datos.news.application.community_news import (
    PER_OUTLET,
    WINDOW_DAYS,
    ClassifiedArticle,
    CommunityNewsReader,
    community_news,
)
from datos.territories.routes import TerritoryReader
from datos.territories.territory import Level

DESCRIPTION = f"""
The news of the last {WINDOW_DAYS} days (today included, Spain time) that the active classifier
placed in this community and sector, at most {PER_OUTLET} per outlet (its newest).

**Order:** publication time, newest first; ties by outlet id. The order never depends on an
outlet's size, audience or line.

No item names a party (ADR-0018): who governs the community is in
`/communities/{{territory_id}}/governments`.
"""


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


class CommunityNewsOut(BaseModel):
    territory_id: str
    sector_id: str
    since: date
    items: list[NewsItemOut]


def build_news_router(
    *,
    news: Provider[CommunityNewsReader],
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
        )
        return CommunityNewsOut(
            territory_id=result.territory_id,
            sector_id=result.sector_id,
            since=result.since,
            items=[_item(item) for item in result.items],
        )

    return router


def _item(article: ClassifiedArticle) -> NewsItemOut:
    return NewsItemOut(
        outlet_id=article.outlet_id,
        outlet_name=article.outlet_name,
        headline=article.headline,
        url=article.url,
        published_at=article.published_at,
        classified_by=ClassifierOut(model_id=article.model_id, model_version=article.model_version),
    )
