from datetime import date
from decimal import Decimal

import pytest

from datos.indicators.domain.definitions import INDICATORS
from datos.indicators.domain.indicator import (
    COMMUNITY_CODES,
    IndicatorDefinition,
    IndicatorSourceError,
    Observation,
    Periodicity,
    SeriesInfo,
    changed_only,
    check_series_shape,
    observation,
    select_series,
)

RATE = IndicatorDefinition(
    id="unemployment_rate",
    name="Tasa de paro",
    unit="%",
    periodicity=Periodicity.QUARTERLY,
    source_table_id="14506",
    description="d",
    selector={18: "Ambos sexos", 356: "Total"},
    unit_id=135,
    scale_id=1,
)


def _series(code: str, community: str | None, sex: str = "Ambos sexos") -> SeriesInfo:
    return SeriesInfo(code, community, {18: sex, 356: "Total", 70: "x"})


def _all_communities() -> list[SeriesInfo]:
    return [_series(f"S{c}", c) for c in COMMUNITY_CODES]


def test_one_series_per_community_is_chosen_by_metadata() -> None:
    noise = [_series("NAT", None), _series("MEN01", "01", sex="Hombres")]

    chosen = select_series(RATE, _all_communities() + noise)

    assert len(chosen) == 19
    assert chosen["01"] == "S01" and chosen["19"] == "S19"


def test_a_missing_community_stops_the_load() -> None:
    without_melilla = [s for s in _all_communities() if s.community_code != "19"]

    with pytest.raises(IndicatorSourceError, match="no series for \\['19'\\]"):
        select_series(RATE, without_melilla)


def test_two_matching_series_for_a_community_stop_the_load() -> None:
    with pytest.raises(IndicatorSourceError, match="several"):
        select_series(RATE, [*_all_communities(), _series("DUP", "05")])


def test_a_series_with_another_unit_or_scale_stops_the_load() -> None:
    check_series_shape(RATE, unit_id=135, scale_id=1)

    with pytest.raises(IndicatorSourceError, match="expected unit 135 and scale 1"):
        check_series_shape(RATE, unit_id=135, scale_id=4)


def test_an_observation_keeps_the_ine_period_and_its_start() -> None:
    o = observation(RATE, "05", "EPA1", year=2026, period_code=20, value=Decimal("14.56"))

    assert (o.territory_id, o.period_start, o.value) == (
        "ccaa-05",
        date(2026, 4, 1),
        Decimal("14.56"),
    )


def test_an_annual_code_in_a_quarterly_indicator_is_refused() -> None:
    with pytest.raises(IndicatorSourceError, match="does not fit quarterly"):
        observation(RATE, "05", "EPA1", year=2026, period_code=28, value=Decimal(1))


def _obs(value: str, start: date = date(2026, 4, 1)) -> Observation:
    return Observation("unemployment_rate", "ccaa-05", 2026, 20, start, Decimal(value), "EPA1")


def test_an_identical_value_adds_nothing_and_a_revised_one_adds_a_row() -> None:
    stored = {date(2026, 4, 1): Decimal("14.66")}

    assert changed_only([_obs("14.66")], stored) == []
    assert changed_only([_obs("14.56")], stored) == [_obs("14.56")]


def test_a_value_returning_to_an_older_one_is_still_a_change() -> None:
    # A -> B -> A: only the latest stored value (B) is compared.
    assert changed_only([_obs("14.66")], {date(2026, 4, 1): Decimal("14.56")}) == [_obs("14.66")]


def test_a_new_period_is_always_added() -> None:
    assert changed_only([_obs("10", date(2026, 7, 1))], {date(2026, 4, 1): Decimal(10)})


def test_the_five_definitions_have_unique_ids_and_known_scales() -> None:
    ids = [d.id for d in INDICATORS]

    assert len(ids) == len(set(ids)) == 5
    assert all(d.scale_factor > 0 for d in INDICATORS)
