"""`GET /territories`: the communities, in a stable order (INE code)."""

from typing import Annotated, Protocol

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from datos.api.provider import Provider
from datos.territories.territory import Level, Territory


class TerritoryReader(Protocol):
    def by_level(self, level: Level) -> list[Territory]: ...


class TerritoryOut(BaseModel):
    id: str
    ine_code: str | None
    name: str


def build_territories_router(reader: Provider[TerritoryReader]) -> APIRouter:
    router = APIRouter(tags=["territories"])

    @router.get("/territories", response_model=list[TerritoryOut])
    def territories(
        territory_reader: Annotated[TerritoryReader, Depends(reader)], level: Level = Level.CCAA
    ) -> list[TerritoryOut]:
        # The `es` row is only the anchor of the State's terms (ADR-0011): never listed.
        return [
            TerritoryOut(id=t.id, ine_code=t.ine_code, name=t.name)
            for t in territory_reader.by_level(level)
            if t.level is not Level.STATE
        ]

    return router
