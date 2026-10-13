from datetime import date

import pytest

from datos.indicators.domain.period import Period, UnknownPeriodError, period_from_ine


def test_code_28_is_the_whole_year_starting_in_january() -> None:
    period = period_from_ine(2025, 28)

    assert period == Period(2025, None)
    assert period.start == date(2025, 1, 1)


@pytest.mark.parametrize(
    ("code", "quarter", "start"),
    [
        (19, 1, date(2026, 1, 1)),
        (20, 2, date(2026, 4, 1)),
        (21, 3, date(2026, 7, 1)),
        (22, 4, date(2026, 10, 1)),
    ],
)
def test_codes_19_to_22_are_the_quarters(code: int, quarter: int, start: date) -> None:
    period = period_from_ine(2026, code)

    assert period.quarter == quarter
    assert period.start == start


@pytest.mark.parametrize("code", [1, 18, 23, 27, 29])
def test_any_other_code_is_rejected_not_guessed(code: int) -> None:
    with pytest.raises(UnknownPeriodError, match=str(code)):
        period_from_ine(2026, code)
