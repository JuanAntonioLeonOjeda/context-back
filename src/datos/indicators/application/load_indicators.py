"""Use case: load the latest INE values of every indicator for every community.

For each indicator: list the table's series, pick one per community by metadata, read
its last values, and store only those that changed since the last load, with the download
that produced them, in one transaction per series.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

import structlog

from datos.indicators.domain.indicator import (
    IndicatorDefinition,
    Observation,
    Periodicity,
    SeriesInfo,
    changed_only,
    check_series_shape,
    observation,
    select_series,
    territory_id_of,
)

log = structlog.get_logger(__name__)

HISTORY_YEARS = 6  # enough for the card's series and to catch revisions of recent years


@dataclass(frozen=True, slots=True)
class PublishedValue:
    year: int
    period_code: int
    value: Decimal | None


@dataclass(frozen=True, slots=True)
class SeriesValues:
    unit_id: int
    scale_id: int
    values: Sequence[PublishedValue]
    url: str
    sha256: str


class IndicatorSource(Protocol):
    def series_of_table(self, table_id: str) -> list[SeriesInfo]: ...

    def series_values(self, series_code: str, *, last: int) -> SeriesValues: ...


class IndicatorRepository(Protocol):
    def upsert_indicators(self, definitions: Sequence[IndicatorDefinition]) -> None: ...

    def latest_values(self, indicator_id: str, territory_id: str) -> dict[date, Decimal]:
        """Latest stored value per period start."""
        ...

    def record(self, *, url: str, sha256: str, observations: Sequence[Observation]) -> None:
        """Store one download and its observations atomically."""
        ...


def load_indicators(
    definitions: Sequence[IndicatorDefinition],
    source: IndicatorSource,
    repository: IndicatorRepository,
    *,
    history_years: int = HISTORY_YEARS,
) -> int:
    """Return how many observations were added."""
    repository.upsert_indicators(definitions)
    added = sum(_load(d, source, repository, history_years) for d in definitions)
    log.info("indicators_loaded", indicators=len(definitions), observations_added=added)
    return added


def _load(
    definition: IndicatorDefinition,
    source: IndicatorSource,
    repository: IndicatorRepository,
    history_years: int,
) -> int:
    chosen = select_series(definition, source.series_of_table(definition.source_table_id))
    per_year = 1 if definition.periodicity is Periodicity.ANNUAL else 4
    added = 0
    for community_code, series_code in sorted(chosen.items()):
        values = source.series_values(series_code, last=history_years * per_year)
        check_series_shape(definition, unit_id=values.unit_id, scale_id=values.scale_id)
        downloaded = [
            observation(
                definition,
                community_code,
                series_code,
                year=v.year,
                period_code=v.period_code,
                value=v.value,
            )
            for v in values.values
            if v.value is not None  # not published: no row, so the API answers null
        ]
        territory_id = territory_id_of(community_code)
        new = changed_only(downloaded, repository.latest_values(definition.id, territory_id))
        if new:
            repository.record(url=values.url, sha256=values.sha256, observations=new)
        added += len(new)
    log.info("indicator_loaded", indicator=definition.id, observations_added=added)
    return added
