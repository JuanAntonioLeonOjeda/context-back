"""`GET /communities/{id}/stories`: the recent stories of a community, as groups of articles.
Headline, link and date only: never the lead (sources audit, section 7), a vector or a similarity,
and no party (ADR-0018).
"""

from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from datos.api.provider import Provider
from datos.clock import Clock
from datos.stories.application.community_stories import (
    MAX_STORIES,
    WINDOW_DAYS,
    CommunityStoriesReader,
    CommunityStory,
    StoryArticle,
    StoryRun,
    community_stories,
)
from datos.territories.routes import TerritoryReader
from datos.territories.territory import Level

DESCRIPTION = f"""
The stories of the last {WINDOW_DAYS} days (today included, Spain time): groups of articles from
different outlets about the same event. A story belongs to this community (and sector, when
given) when more than half of its articles are classified there by the active classifier. At most
{MAX_STORIES} stories.

**Order:** stories by their newest article, newest first, ties by story id; inside a story, articles
by outlet id, then publication time. The order never depends on an outlet's size, audience or line.

`grouping` says how the stories were made: the threshold is provisional until pairs are labelled
by hand. It is `null` until the first grouping run exists.
"""


class ArticleOut(BaseModel):
    outlet_id: str
    outlet_name: str
    headline: str
    url: str
    published_at: datetime


class StoryOut(BaseModel):
    story_id: int
    articles: list[ArticleOut]


class GroupingOut(BaseModel):
    run_id: int
    encoder_version: str
    threshold: float
    window_days: int
    created_at: datetime


class CommunityStoriesOut(BaseModel):
    territory_id: str
    sector_id: str | None
    since: date
    grouping: GroupingOut | None
    stories: list[StoryOut]


def build_stories_router(
    *,
    stories: Provider[CommunityStoriesReader],
    territories: Provider[TerritoryReader],
    clock: Clock,
    classifier_id: str,
) -> APIRouter:
    router = APIRouter(tags=["stories"])

    @router.get(
        "/communities/{territory_id}/stories",
        response_model=CommunityStoriesOut,
        description=DESCRIPTION,
    )
    def community(
        territory_id: str,
        stories_reader: Annotated[CommunityStoriesReader, Depends(stories)],
        territory_reader: Annotated[TerritoryReader, Depends(territories)],
        sector: Annotated[
            str | None, Query(description="A sector id: education, health or housing")
        ] = None,
    ) -> CommunityStoriesOut:
        if territory_id not in {t.id for t in territory_reader.by_level(Level.CCAA)}:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown community {territory_id}")
        if sector is not None and sector not in stories_reader.sector_ids():
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"unknown sector {sector}")
        result = community_stories(
            territory_id=territory_id,
            sector_id=sector,
            today=clock.today(),
            model_id=classifier_id,
            stories=stories_reader,
        )
        return CommunityStoriesOut(
            territory_id=result.territory_id,
            sector_id=result.sector_id,
            since=result.since,
            grouping=_grouping(result.run),
            stories=[_story(story) for story in result.stories],
        )

    return router


def _grouping(run: StoryRun | None) -> GroupingOut | None:
    if run is None:
        return None
    return GroupingOut(
        run_id=run.run_id,
        encoder_version=run.encoder_version,
        threshold=run.threshold,
        window_days=run.window_days,
        created_at=run.created_at,
    )


def _story(story: CommunityStory) -> StoryOut:
    return StoryOut(story_id=story.story_id, articles=[_article(a) for a in story.articles])


def _article(article: StoryArticle) -> ArticleOut:
    return ArticleOut(
        outlet_id=article.outlet_id,
        outlet_name=article.outlet_name,
        headline=article.headline,
        url=article.url,
        published_at=article.published_at,
    )
