"""Health endpoint: reports whether the API can reach its database."""

from enum import StrEnum
from typing import Protocol

from fastapi import APIRouter, Response, status
from pydantic import BaseModel


class DatabaseProbe(Protocol):
    """Checks that the database answers. Implementations never raise."""

    def is_reachable(self) -> bool: ...


class ComponentStatus(StrEnum):
    UP = "up"
    DOWN = "down"


class HealthResponse(BaseModel):
    database: ComponentStatus


def build_health_router(probe: DatabaseProbe) -> APIRouter:
    router = APIRouter()

    @router.get(
        "/health",
        response_model=HealthResponse,
        # Declared so the OpenAPI contract, and the web client generated from it, know
        # that a database that does not answer is a 503 with this same body.
        responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": HealthResponse}},
    )
    def health(response: Response) -> HealthResponse:
        if probe.is_reachable():
            return HealthResponse(database=ComponentStatus.UP)
        # 503 so that orchestrators and the web app can tell "running but unusable".
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(database=ComponentStatus.DOWN)

    return router
