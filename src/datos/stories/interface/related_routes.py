"""`GET /articles/{id}/related`: the news related to one news item, a chain back in time (spec
related-news). Headline, link, outlet and date only: never the lead (sources audit, section 7), a
vector or a party (ADR-0018). The similarity of each step is shown: a relation is a measure of how
alike two texts are, and the reader should see how strong it is.
"""

from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from datos.api.provider import Provider
from datos.stories.application.related_news import RelatedNews, RelatedReader, related_news
from datos.stories.domain.related import ChainLink, NewsItem, RelatedSettings

DESCRIPTION = """
The news related to a news item: from it, the most similar earlier news item, then the most
similar earlier than that one, and so on. Similar means alike in text (cosine similarity of the
sentence vectors of headline and lead); it does not say that one caused the other.

A step must be at least `step_threshold` to the step before it and `origin_threshold` to the news
item asked for, within `window_days` before the step; the same outlet publishing the same news
again is left out; the chain covers at most `max_days` days. The values are provisional and come
with every answer.

**Order:** days newest first; inside a day, the order in which the items joined the chain. The
first item of the first day is the news item asked for (`similarity` null). An item no worker has
embedded yet has no related news. 404: no article with that id.
"""


class RelatedItemOut(BaseModel):
    article_id: int
    outlet_id: str
    outlet_name: str
    headline: str
    url: str
    published_at: datetime
    similarity: float | None  # to the step before it; null for the news item asked for


class RelatedDayOut(BaseModel):
    day: date  # in Spain
    items: list[RelatedItemOut]


class RelatedSettingsOut(BaseModel):
    step_threshold: float
    origin_threshold: float
    window_days: int
    max_days: int


class RelatedNewsOut(BaseModel):
    article_id: int
    settings: RelatedSettingsOut
    days: list[RelatedDayOut]


def build_related_router(*, related: Provider[RelatedReader]) -> APIRouter:
    router = APIRouter(tags=["stories"])

    @router.get(
        "/articles/{article_id}/related", response_model=RelatedNewsOut, description=DESCRIPTION
    )
    def chain(
        article_id: int, reader: Annotated[RelatedReader, Depends(related)]
    ) -> RelatedNewsOut:
        found = related_news(reader, article_id)
        if found is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"no article {article_id}")
        return _out(found)

    return router


def _out(found: RelatedNews) -> RelatedNewsOut:
    return RelatedNewsOut(
        article_id=found.item.article_id,
        settings=_settings(found.settings),
        days=[
            RelatedDayOut(day=day.day, items=[_item(link) for link in day.links])
            for day in found.days
        ],
    )


def _settings(settings: RelatedSettings) -> RelatedSettingsOut:
    return RelatedSettingsOut(
        step_threshold=settings.step_threshold,
        origin_threshold=settings.origin_threshold,
        window_days=settings.window_days,
        max_days=settings.max_days,
    )


def _item(link: ChainLink) -> RelatedItemOut:
    item: NewsItem = link.item
    return RelatedItemOut(
        article_id=item.article_id,
        outlet_id=item.outlet_id,
        outlet_name=item.outlet_name,
        headline=item.headline,
        url=item.url,
        published_at=item.published_at,
        similarity=None if link.similarity is None else round(link.similarity, 3),
    )
