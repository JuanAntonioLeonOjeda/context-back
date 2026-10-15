"""Read side: the indicators of one community, as the card shows them.

The assembly is pure: the reader returns stored rows; this module applies the scale,
orders the series and picks the latest value. An indicator without any value for the
community is still returned, with `latest` None: no data is never shown as 0.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from datos.indicators.domain.period import Period, period_from_ine


@dataclass(frozen=True, slots=True)
class IndicatorInfo:
    id: str
    name: str
    unit: str
    scale_factor: Decimal
    periodicity: str
    source_table_id: str


@dataclass(frozen=True, slots=True)
class StoredValue:
    """A current observation (latest download per period) of one community."""

    indicator_id: str
    period_year: int
    period_code: int
    value: Decimal
    source_series_code: str
    fetched_at: datetime


@dataclass(frozen=True, slots=True)
class Point:
    period: Period
    value: Decimal  # in the indicator's unit (scale applied)


@dataclass(frozen=True, slots=True)
class CommunityIndicator:
    info: IndicatorInfo
    series: tuple[Point, ...]  # oldest first
    source_series_code: str | None
    fetched_at: datetime | None  # of the newest download among the values shown

    @property
    def latest(self) -> Point | None:
        return self.series[-1] if self.series else None


class IndicatorReader(Protocol):
    def indicators(self) -> list[IndicatorInfo]: ...

    def current_values(self, territory_id: str) -> list[StoredValue]: ...


def community_indicators(
    indicators: Sequence[IndicatorInfo], values: Sequence[StoredValue]
) -> list[CommunityIndicator]:
    """One entry per indicator, alphabetical by id (a stable order with no ranking)."""
    return [
        _one(info, [v for v in values if v.indicator_id == info.id])
        for info in sorted(indicators, key=lambda i: i.id)
    ]


def _one(info: IndicatorInfo, values: list[StoredValue]) -> CommunityIndicator:
    points = sorted(
        (
            Point(period_from_ine(v.period_year, v.period_code), v.value * info.scale_factor)
            for v in values
        ),
        key=lambda p: p.period.start,
    )
    newest = max(values, key=lambda v: v.fetched_at, default=None)
    return CommunityIndicator(
        info=info,
        series=tuple(points),
        source_series_code=values[0].source_series_code if values else None,
        fetched_at=newest.fetched_at if newest else None,
    )
