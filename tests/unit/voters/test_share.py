from decimal import Decimal

import pytest

from datos.voters.domain.municipal_value import MunicipalValue
from datos.voters.domain.share import (
    Component,
    ShareCount,
    share_percentage,
    share_values,
)


@pytest.mark.parametrize(
    ("part", "total", "expected"),
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
    part: int, total: int, expected: str
) -> None:
    assert share_percentage(part, total) == Decimal(expected)


def test_a_municipality_without_population_has_no_percentage() -> None:
    assert share_percentage(0, 0) is None


@pytest.mark.parametrize(("part", "total"), [(51, 50), (-1, 50), (1, -50), (-1, -1)])
def test_counts_that_cannot_be_true_are_refused(part: int, total: int) -> None:
    with pytest.raises(ValueError, match="the part cannot be more than the whole"):
        share_percentage(part, total)


def _counts(code: str, part: int, total: int) -> list[ShareCount]:
    return [
        ShareCount(code, Component.TOTAL, total),
        ShareCount(code, Component.PART, part),
    ]


def test_every_municipality_gets_its_percentage_in_order_of_code() -> None:
    counts = _counts("28079", 1_354_780, 2_925_135) + _counts("01006", 84, 207)

    values, problems = share_values(counts, 2023)

    assert problems == []
    assert values == [
        MunicipalValue("01006", 2023, Decimal("40.580")),  # 84 / 207 = 0.405797…
        MunicipalValue("28079", 2023, Decimal("46.315")),  # 1354780 / 2925135 = 0.463151…
    ]


def test_a_municipality_without_population_is_left_out_without_a_problem() -> None:
    assert share_values(_counts("01006", 0, 0), 2023) == ([], [])


def test_a_count_in_two_files_is_a_problem() -> None:
    counts = [*_counts("01006", 84, 207), ShareCount("01006", Component.TOTAL, 207)]

    values, problems = share_values(counts, 2023)

    assert problems == ["municipality 01006: total is repeated"]
    assert values != []  # the other municipalities are still checked, all problems come at once


@pytest.mark.parametrize(
    ("kept", "missing"), [(Component.TOTAL, "part"), (Component.PART, "total")]
)
def test_a_municipality_with_only_one_of_the_counts_is_a_problem(
    kept: Component, missing: str
) -> None:
    values, problems = share_values([ShareCount("01006", kept, 50)], 2023)

    assert values == []
    assert problems == [f"municipality 01006: no {missing} count"]


def test_a_part_above_its_total_is_a_problem() -> None:
    values, problems = share_values(_counts("01006", 208, 207), 2023)

    assert values == []
    assert problems == [
        "municipality 01006: 208 out of 207: the part cannot be more than the whole"
    ]


def test_all_the_problems_come_at_once() -> None:
    counts = [*_counts("01006", 208, 207), ShareCount("01011", Component.TOTAL, 5)]

    _, problems = share_values(counts, 2023)

    assert len(problems) == 2
