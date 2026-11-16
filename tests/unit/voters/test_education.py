from decimal import Decimal

import pytest

from datos.voters.domain.education import education_percentage


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
