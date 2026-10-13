"""FastAPI application factory."""

from fastapi import FastAPI

from datos.api.health import DatabaseProbe, build_health_router


def create_app(database_probe: DatabaseProbe) -> FastAPI:
    app = FastAPI(title="datos", version="0.1.0")
    app.include_router(build_health_router(database_probe))
    return app
