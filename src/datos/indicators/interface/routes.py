"""`GET /communities/{id}/indicators`: the statistics of the community card, with sources."""

from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from datos.api.provider import Provider
from datos.indicators.application.read_indicators import (
    CommunityIndicator,
    IndicatorReader,
    Point,
    community_indicators,
)
from datos.territories.routes import TerritoryReader
from datos.territories.territory import Level

INE_TABLE_URL = "https://www.ine.es/jaxiT3/Tabla.htm?t={table_id}"  # checked for the 5 tables


class PointOut(BaseModel):
    period_start: date
    year: int
    quarter: int | None
    value: float


class SourceOut(BaseModel):
    publisher: str
    table_id: str
    table_url: str
    series_code: str | None
    fetched_at: datetime | None


class IndicatorOut(BaseModel):
    indicator_id: str
    name: str
    unit: str
    periodicity: str
    latest: PointOut | None  # None: the INE publishes no value for this community
    series: list[PointOut]
    source: SourceOut


def build_indicators_router(
    indicators: Provider[IndicatorReader], territories: Provider[TerritoryReader]
) -> APIRouter:
    router = APIRouter(tags=["indicators"])

    @router.get("/communities/{territory_id}/indicators", response_model=list[IndicatorOut])
    def community(
        territory_id: str,
        reader: Annotated[IndicatorReader, Depends(indicators)],
        territory_reader: Annotated[TerritoryReader, Depends(territories)],
    ) -> list[IndicatorOut]:
        if territory_id not in {t.id for t in territory_reader.by_level(Level.CCAA)}:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown community {territory_id}")
        rows = community_indicators(reader.indicators(), reader.current_values(territory_id))
        return [_out(row) for row in rows]

    return router


def _point(point: Point) -> PointOut:
    return PointOut(
        period_start=point.period.start,
        year=point.period.year,
        quarter=point.period.quarter,
        value=float(point.value),
    )


def _out(row: CommunityIndicator) -> IndicatorOut:
    latest = row.latest
    return IndicatorOut(
        indicator_id=row.info.id,
        name=row.info.name,
        unit=row.info.unit,
        periodicity=row.info.periodicity,
        latest=_point(latest) if latest else None,
        series=[_point(p) for p in row.series],
        source=SourceOut(
            publisher="INE",
            table_id=row.info.source_table_id,
            table_url=INE_TABLE_URL.format(table_id=row.info.source_table_id),
            series_code=row.source_series_code,
            fetched_at=row.fetched_at,
        ),
    )
