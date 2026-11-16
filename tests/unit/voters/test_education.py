from decimal import Decimal

import pytest

from datos.voters.domain.education import (
    EducationCount,
    EducationLevel,
    education_percentage,
    education_values,
)
from datos.voters.domain.municipal_value import MunicipalValue


@pytest.mark.parametrize(
    ("higher", "total", "expected"),
    [
        (463, 1000, "46.300"),  # an exact figure keeps its three decimals
        (1, 8, "12.500"),
        (1, 3, "33.333"),  # rounds down
        (2, 3, "66.667"),  # rounds up
        (1, 200_000, "0.001"),  # 0.0005 exactly: half up (half-even would give 0.000)
        (0, 50, "0.000"),
        (50, 50, "100.000"),
    ],
)
def test_the_percentage_has_three_decimals_and_rounds_halves_up(
    higher: int, total: int, expected: str
) -> None:
    assert education_percentage(higher, total) == Decimal(expected)


def test_a_municipality_without_population_has_no_percentage() -> None:
    assert education_percentage(0, 0) is None


@pytest.mark.parametrize(("higher", "total"), [(51, 50), (-1, 50), (1, -50), (-1, -1)])
def test_counts_that_cannot_be_true_are_refused(higher: int, total: int) -> None:
    with pytest.raises(ValueError, match="higher education"):
        education_percentage(higher, total)


def _counts(code: str, higher: int, total: int) -> list[EducationCount]:
    return [
        EducationCount(code, EducationLevel.TOTAL, total),
        EducationCount(code, EducationLevel.HIGHER, higher),
    ]


def test_every_municipality_gets_its_percentage_in_order_of_code() -> None:
    counts = _counts("28079", 1_354_780, 2_925_135) + _counts("01006", 84, 207)

    values, problems = education_values(counts, 2023)

    assert problems == []
    assert values == [
        MunicipalValue("01006", 2023, Decimal("40.580")),  # 84 / 207 = 0.405797…
        MunicipalValue("28079", 2023, Decimal("46.315")),  # 1354780 / 2925135 = 0.463151…
    ]


def test_a_municipality_without_population_is_left_out_without_a_problem() -> None:
    assert education_values(_counts("01006", 0, 0), 2023) == ([], [])


def test_a_count_in_two_files_is_a_problem() -> None:
    counts = [*_counts("01006", 84, 207), EducationCount("01006", EducationLevel.TOTAL, 207)]

    values, problems = education_values(counts, 2023)

    assert problems == ["municipality 01006: total is repeated"]
    assert values != []  # the other municipalities are still checked, all problems come at once


@pytest.mark.parametrize(
    ("kept", "missing"), [(EducationLevel.TOTAL, "higher"), (EducationLevel.HIGHER, "total")]
)
def test_a_municipality_with_only_one_of_the_counts_is_a_problem(
    kept: EducationLevel, missing: str
) -> None:
    values, problems = education_values([EducationCount("01006", kept, 50)], 2023)

    assert values == []
    assert problems == [f"municipality 01006: no {missing} count"]


def test_more_people_with_higher_education_than_people_is_a_problem() -> None:
    values, problems = education_values(_counts("01006", 208, 207), 2023)

    assert values == []
    assert problems == ["municipality 01006: 208 with higher education out of 207"]


def test_all_the_problems_come_at_once() -> None:
    counts = [*_counts("01006", 208, 207), EducationCount("01011", EducationLevel.TOTAL, 5)]

    _, problems = education_values(counts, 2023)

    assert len(problems) == 2
