"""Indicator definitions and the rules that turn INE series into observations.

Pure. Which series feeds each indicator is chosen by its metadata (variable → value), not
by its name, and every choice is checked: exactly one series per community, with the unit
and scale the definition expects. If the INE changes a table, loading fails loudly.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from datos.indicators.domain.period import ANNUAL_CODE, period_from_ine

COMMUNITY_CODES = tuple(f"{n:02d}" for n in range(1, 20))  # INE 01-19, Ceuta and Melilla included
# INE "Escala" ids verified on 2026-10-13: 1 is units, 4 is thousands.
SCALE_FACTORS = {1: Decimal(1), 4: Decimal(1000)}


class Periodicity(StrEnum):
    ANNUAL = "annual"
    QUARTERLY = "quarterly"


class IndicatorSourceError(Exception):
    """The INE data no longer matches a definition (series, unit, scale or period)."""


@dataclass(frozen=True, slots=True)
class IndicatorDefinition:
    id: str
    name: str  # the measure, shown to users; no evaluative words
    unit: str
    periodicity: Periodicity
    source_table_id: str
    description: str
    # INE variable id → value name that the series must have (besides the community).
    selector: Mapping[int, str]
    unit_id: int  # INE "Unidad" the series must have
    scale_id: int  # INE "Escala" the series must have

    @property
    def scale_factor(self) -> Decimal:
        return SCALE_FACTORS[self.scale_id]


@dataclass(frozen=True, slots=True)
class SeriesInfo:
    """What the domain needs to know about an INE series."""

    code: str
    community_code: str | None
    values: Mapping[int, str]  # variable id → value name


@dataclass(frozen=True, slots=True)
class Observation:
    indicator_id: str
    territory_id: str
    period_year: int
    period_code: int
    period_start: date
    value: Decimal
    source_series_code: str


def territory_id_of(community_code: str) -> str:
    return f"ccaa-{community_code}"


def select_series(definition: IndicatorDefinition, series: Iterable[SeriesInfo]) -> dict[str, str]:
    """Community code → series code: exactly one matching series per community."""
    found: dict[str, list[str]] = {}
    for s in series:
        if s.community_code in COMMUNITY_CODES and _matches(definition.selector, s.values):
            found.setdefault(s.community_code, []).append(s.code)
    missing = [c for c in COMMUNITY_CODES if c not in found]
    repeated = {c: codes for c, codes in found.items() if len(codes) > 1}
    if missing or repeated:
        raise IndicatorSourceError(
            f"{definition.id}: table {definition.source_table_id} has no series for {missing}"
            f" and several for {repeated}"
        )
    return {community: codes[0] for community, codes in found.items()}


def check_series_shape(definition: IndicatorDefinition, *, unit_id: int, scale_id: int) -> None:
    if (unit_id, scale_id) != (definition.unit_id, definition.scale_id):
        raise IndicatorSourceError(
            f"{definition.id}: expected unit {definition.unit_id} and scale"
            f" {definition.scale_id}, the INE sent {unit_id} and {scale_id}"
        )


def observation(
    definition: IndicatorDefinition,
    community_code: str,
    series_code: str,
    *,
    year: int,
    period_code: int,
    value: Decimal,
) -> Observation:
    """One published value as an observation; its period must fit the periodicity."""
    if (period_code == ANNUAL_CODE) != (definition.periodicity is Periodicity.ANNUAL):
        raise IndicatorSourceError(
            f"{definition.id}: period code {period_code} does not fit {definition.periodicity}"
        )
    period = period_from_ine(year, period_code)
    return Observation(
        indicator_id=definition.id,
        territory_id=territory_id_of(community_code),
        period_year=year,
        period_code=period_code,
        period_start=period.start,
        value=value,
        source_series_code=series_code,
    )


def changed_only(
    downloaded: Sequence[Observation], latest: Mapping[date, Decimal]
) -> list[Observation]:
    """The observations whose value differs from the latest stored for their period.

    Append-only (ADR-0012): an identical value adds nothing; a revised one adds a row, even
    if it returns to an older value (A -> B -> A), because only the latest is compared.
    """
    return [o for o in downloaded if latest.get(o.period_start) != o.value]


def _matches(selector: Mapping[int, str], values: Mapping[int, str]) -> bool:
    return all(values.get(variable) == name for variable, name in selector.items())
