from collections.abc import Sequence
from datetime import date
from decimal import Decimal

import pytest

from datos.indicators.application.load_indicators import (
    PublishedValue,
    SeriesValues,
    load_indicators,
)
from datos.indicators.domain.indicator import (
    COMMUNITY_CODES,
    IndicatorDefinition,
    IndicatorSourceError,
    Observation,
    Periodicity,
    SeriesInfo,
)

AROPE = IndicatorDefinition(
    id="poverty_or_exclusion_rate",
    name="AROPE",
    unit="%",
    periodicity=Periodicity.ANNUAL,
    source_table_id="60264",
    description="d",
    selector={356: "Total"},
    unit_id=101,
    scale_id=1,
)
SHA = "b" * 64


class FakeSource:
    def __init__(self, values: dict[str, list[PublishedValue]], *, scale_id: int = 1) -> None:
        self.values = values
        self.scale_id = scale_id
        self.lasts: list[int] = []

    def series_of_table(self, table_id: str) -> list[SeriesInfo]:
        return [SeriesInfo(f"ECV{c}", c, {356: "Total"}) for c in COMMUNITY_CODES]

    def series_values(self, series_code: str, *, last: int) -> SeriesValues:
        self.lasts.append(last)
        community = series_code.removeprefix("ECV")
        default = [PublishedValue(2025, 28, Decimal("30.1"))]
        return SeriesValues(
            101, self.scale_id, self.values.get(community, default), "https://x", SHA
        )


class FakeRepository:
    def __init__(self) -> None:
        self.rows: list[Observation] = []
        self.downloads = 0

    def upsert_indicators(self, definitions: Sequence[IndicatorDefinition]) -> None:
        pass

    def latest_values(self, indicator_id: str, territory_id: str) -> dict[date, Decimal]:
        latest: dict[date, Decimal] = {}
        for o in self.rows:  # rows are appended in order: the last one wins
            if (o.indicator_id, o.territory_id) == (indicator_id, territory_id):
                latest[o.period_start] = o.value
        return latest

    def record(self, *, url: str, sha256: str, observations: Sequence[Observation]) -> None:
        self.downloads += 1
        self.rows.extend(observations)


def test_loads_one_value_per_community_and_a_second_run_adds_nothing() -> None:
    source, repository = FakeSource({}), FakeRepository()

    first = load_indicators([AROPE], source, repository)
    second = load_indicators([AROPE], source, repository)

    assert (first, second) == (19, 0)
    assert repository.downloads == 19  # a download is stored only when it adds rows


def test_a_revised_value_adds_one_row() -> None:
    repository = FakeRepository()
    load_indicators([AROPE], FakeSource({}), repository)

    revised = FakeSource({"05": [PublishedValue(2025, 28, Decimal("29.9"))]})
    added = load_indicators([AROPE], revised, repository)

    assert added == 1
    assert repository.latest_values(AROPE.id, "ccaa-05") == {date(2025, 1, 1): Decimal("29.9")}


def test_an_unpublished_value_is_not_stored() -> None:
    source = FakeSource({"18": [PublishedValue(2025, 28, None)]})
    repository = FakeRepository()

    load_indicators([AROPE], source, repository)

    assert repository.latest_values(AROPE.id, "ccaa-18") == {}


def test_history_covers_six_years_for_annual_series() -> None:
    source = FakeSource({})

    load_indicators([AROPE], source, FakeRepository())

    assert set(source.lasts) == {6}


def test_a_change_of_scale_at_the_ine_stops_the_load() -> None:
    with pytest.raises(IndicatorSourceError, match="expected unit 101 and scale 1"):
        load_indicators([AROPE], FakeSource({}, scale_id=4), FakeRepository())
