"""Composition root: settings → logging → database → API.

Run with: uv run uvicorn datos.main:app --factory
"""

import json
from pathlib import Path

from fastapi import FastAPI

from datos.api.app import create_app
from datos.api.provider import built_on, per_request
from datos.clock import SystemClock
from datos.config import load_settings
from datos.db import SqlDatabaseProbe, build_engine
from datos.governments.infrastructure.pg_reader import PgGovernmentsReader
from datos.indicators.infrastructure.pg_reader import PgIndicatorReader
from datos.log_setup import configure_logging
from datos.news.infrastructure.pg_news_reader import PgCommunityNewsReader
from datos.stories.infrastructure.pg_stories_reader import PgCommunityStoriesReader
from datos.stories.infrastructure.pg_story_tree_reader import PgStoryTreeReader
from datos.territories.reader import PgTerritoryReader
from datos.voters.infrastructure.candidature_parties import read_candidature_parties
from datos.voters.infrastructure.pg_voters_reader import PgVotersReader

GEOMETRY = Path("data/geo/ccaa.geojson")
CANDIDATURE_PARTIES = Path("data/voters/candidature-parties.csv")


def app() -> FastAPI:
    settings = load_settings()
    configure_logging(settings.log_level, as_json=settings.log_json)
    engine = build_engine(str(settings.database_url))
    # One read-only connection per request, shared by every reader the request needs and closed
    # when the response is sent: a community page used to open about ten at once.
    connection = per_request(engine.connect)
    return create_app(
        database_probe=SqlDatabaseProbe(engine),
        governments=built_on(connection, PgGovernmentsReader),
        territories=built_on(connection, PgTerritoryReader),
        indicators=built_on(connection, PgIndicatorReader),
        news=built_on(connection, PgCommunityNewsReader),
        stories=built_on(connection, PgCommunityStoriesReader),
        trees=built_on(connection, PgStoryTreeReader),
        voters=built_on(connection, PgVotersReader),
        party_by_candidature=read_candidature_parties(CANDIDATURE_PARTIES),
        clock=SystemClock(),
        geometry=json.loads(GEOMETRY.read_text(encoding="utf-8")),
        classifier_id=settings.active_classifier_id,
    )
