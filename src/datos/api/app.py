"""FastAPI application factory."""

from fastapi import FastAPI

from datos.api.health import DatabaseProbe, build_health_router
from datos.api.provider import Provider
from datos.clock import Clock
from datos.governments.application.read_governments import GovernmentsReader
from datos.governments.interface.routes import build_governments_router
from datos.territories.routes import TerritoryReader, build_territories_router


def create_app(
    database_probe: DatabaseProbe,
    *,
    governments: Provider[GovernmentsReader],
    territories: Provider[TerritoryReader],
    clock: Clock,
) -> FastAPI:
    """`governments` and `territories` are FastAPI dependencies that give one reader per
    request (the composition root opens a database connection for each)."""
    app = FastAPI(title="datos", version="0.1.0")
    app.include_router(build_health_router(database_probe))
    app.include_router(build_territories_router(territories))
    app.include_router(build_governments_router(governments, territories, clock))
    return app
