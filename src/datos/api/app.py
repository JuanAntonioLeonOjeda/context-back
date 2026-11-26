"""FastAPI application factory."""

from collections.abc import Mapping
from typing import Protocol

from fastapi import FastAPI

from datos.api.health import DatabaseProbe, build_health_router
from datos.api.provider import Provider
from datos.clock import Clock
from datos.governments.application.read_governments import GovernmentsReader
from datos.governments.interface.routes import build_governments_router
from datos.indicators.application.read_indicators import IndicatorReader
from datos.indicators.interface.routes import build_indicators_router
from datos.news.application.community_news import CommunityNewsReader
from datos.news.interface.routes import build_news_router
from datos.organization.application.competent_news import CompetenceReader
from datos.organization.application.organization_chart import OrganizationReader
from datos.organization.interface.routes import build_organization_router
from datos.stories.application.community_stories import CommunityStoriesReader
from datos.stories.application.related_news import RelatedReader
from datos.stories.application.story_tree import StoryTreeReader
from datos.stories.interface.related_routes import build_related_router
from datos.stories.interface.routes import build_stories_router
from datos.stories.interface.tree_routes import build_tree_router
from datos.territories.routes import TerritoryReader, build_territories_router
from datos.voters.application.community_voters import PartyByCandidature, VotersReader
from datos.voters.interface.routes import build_voters_router


class OrganizationAndCompetenceReader(OrganizationReader, CompetenceReader, Protocol):
    """The organisation's reader serves the charts and the bodies with competence of the news."""


def create_app(
    database_probe: DatabaseProbe,
    *,
    governments: Provider[GovernmentsReader],
    territories: Provider[TerritoryReader],
    indicators: Provider[IndicatorReader],
    news: Provider[CommunityNewsReader],
    stories: Provider[CommunityStoriesReader],
    trees: Provider[StoryTreeReader],
    related: Provider[RelatedReader],
    voters: Provider[VotersReader],
    organization: Provider[OrganizationAndCompetenceReader],
    party_by_candidature: PartyByCandidature,
    clock: Clock,
    geometry: Mapping[str, object],
    classifier_id: str,
) -> FastAPI:
    """`governments` and `territories` are FastAPI dependencies that give one reader per
    request (the composition root opens a database connection for each). `geometry` is
    the GeoJSON of the communities (`data/geo/ccaa.geojson`); `classifier_id`, the classifier
    whose labels the news API reads; `party_by_candidature`, the curated candidature → party
    table of the voter profiles (data/voters/candidature-parties.csv)."""
    app = FastAPI(title="datos", version="0.1.0")
    app.include_router(build_health_router(database_probe))
    app.include_router(build_territories_router(territories, geometry))
    app.include_router(build_governments_router(governments, territories, clock))
    app.include_router(build_indicators_router(indicators, territories))
    app.include_router(
        build_news_router(
            news=news,
            territories=territories,
            competences=organization,
            clock=clock,
            classifier_id=classifier_id,
        )
    )
    app.include_router(
        build_stories_router(
            stories=stories,
            territories=territories,
            clock=clock,
            classifier_id=classifier_id,
        )
    )
    app.include_router(build_tree_router(trees=trees))
    app.include_router(build_related_router(related=related))
    app.include_router(build_voters_router(voters, governments, territories, party_by_candidature))
    app.include_router(build_organization_router(organization, territories, clock))
    return app
