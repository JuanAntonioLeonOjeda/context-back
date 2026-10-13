"""Composition root: settings → logging → database → API.

Run with: uv run uvicorn datos.main:app --factory
"""

from fastapi import FastAPI

from datos.api.app import create_app
from datos.config import load_settings
from datos.db import SqlDatabaseProbe, build_engine
from datos.log_setup import configure_logging


def app() -> FastAPI:
    settings = load_settings()
    configure_logging(settings.log_level, as_json=settings.log_json)
    engine = build_engine(str(settings.database_url))
    return create_app(database_probe=SqlDatabaseProbe(engine))
