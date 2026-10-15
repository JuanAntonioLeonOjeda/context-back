from datetime import UTC, datetime
from decimal import Decimal

from datos.indicators.application.read_indicators import (
    IndicatorInfo,
    StoredValue,
    community_indicators,
)

RATE = IndicatorInfo("unemployment_rate", "Tasa de paro", "%", Decimal(1), "quarterly", "14506")
IN_THOUSANDS = IndicatorInfo("people", "Personas", "persons", Decimal(1000), "quarterly", "65288")
EARLY = datetime(2026, 7, 1, tzinfo=UTC)
LATE = datetime(2026, 10, 13, tzinfo=UTC)


def _value(indicator_id: str, code: int, value: str, fetched_at: datetime = EARLY) -> StoredValue:
    return StoredValue(indicator_id, 2026, code, Decimal(value), "EPA1", fetched_at)


def test_indicators_come_alphabetically_with_their_series_oldest_first() -> None:
    values = [_value("unemployment_rate", 20, "11.6"), _value("unemployment_rate", 19, "12.1")]

    [people, rate] = community_indicators([RATE, IN_THOUSANDS], values)

    assert (people.info.id, rate.info.id) == ("people", "unemployment_rate")
    assert [p.value for p in rate.series] == [Decimal("12.1"), Decimal("11.6")]
    assert rate.latest is not None and rate.latest.period.quarter == 2


def test_an_indicator_without_values_is_kept_with_no_latest_never_zero() -> None:
    [people, _] = community_indicators(
        [RATE, IN_THOUSANDS], [_value("unemployment_rate", 20, "11.6")]
    )

    assert people.latest is None and people.series == ()
    assert people.source_series_code is None and people.fetched_at is None


def test_the_scale_is_applied_on_read() -> None:
    [people] = community_indicators([IN_THOUSANDS], [_value("people", 20, "18.6")])

    assert people.latest is not None and people.latest.value == Decimal("18600.0")


def test_the_source_date_is_the_newest_download_among_the_values() -> None:
    values = [
        _value("unemployment_rate", 19, "12.1", EARLY),
        _value("unemployment_rate", 20, "11.6", LATE),
    ]

    [rate] = community_indicators([RATE], values)

    assert rate.fetched_at == LATE
