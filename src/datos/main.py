"""Composition root: settings → logging → database → API.

Run with: uv run uvicorn datos.main:app --factory
"""

import json
from collections.abc import Callable, Iterator
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy import Engine

from datos.api.app import create_app
from datos.clock import SystemClock
from datos.config import load_settings
from datos.db import SqlDatabaseProbe, build_engine
from datos.governments.infrastructure.pg_reader import PgCompetencesReader, PgGovernmentsReader
from datos.indicators.infrastructure.pg_reader import PgIndicatorReader
from datos.log_setup import configure_logging
from datos.news.infrastructure.pg_news_reader import PgCommunityNewsReader
from datos.territories.reader import PgTerritoryReader

GEOMETRY = Path("data/geo/ccaa.geojson")


def app() -> FastAPI:
    settings = load_settings()
    configure_logging(settings.log_level, as_json=settings.log_json)
    engine = build_engine(str(settings.database_url))
    return create_app(
        database_probe=SqlDatabaseProbe(engine),
        governments=_governments_reader(engine),
        territories=_territory_reader(engine),
        indicators=_indicator_reader(engine),
        competences=_competences_reader(engine),
        news=_news_reader(engine),
        clock=SystemClock(),
        geometry=json.loads(GEOMETRY.read_text(encoding="utf-8")),
        classifier_id=settings.active_classifier_id,
    )


# One read-only connection per request, closed when the response is sent.
def _governments_reader(engine: Engine) -> Callable[[], Iterator[PgGovernmentsReader]]:
    def dependency() -> Iterator[PgGovernmentsReader]:
        with engine.connect() as connection:
            yield PgGovernmentsReader(connection)

    return dependency


def _territory_reader(engine: Engine) -> Callable[[], Iterator[PgTerritoryReader]]:
    def dependency() -> Iterator[PgTerritoryReader]:
        with engine.connect() as connection:
            yield PgTerritoryReader(connection)

    return dependency


def _indicator_reader(engine: Engine) -> Callable[[], Iterator[PgIndicatorReader]]:
    def dependency() -> Iterator[PgIndicatorReader]:
        with engine.connect() as connection:
            yield PgIndicatorReader(connection)

    return dependency


def _competences_reader(engine: Engine) -> Callable[[], Iterator[PgCompetencesReader]]:
    def dependency() -> Iterator[PgCompetencesReader]:
        with engine.connect() as connection:
            yield PgCompetencesReader(connection)

    return dependency


def _news_reader(engine: Engine) -> Callable[[], Iterator[PgCommunityNewsReader]]:
    def dependency() -> Iterator[PgCommunityNewsReader]:
        with engine.connect() as connection:
            yield PgCommunityNewsReader(connection)

    return dependency
