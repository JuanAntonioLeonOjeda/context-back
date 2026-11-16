"""Share of a municipality's population with higher education, from the INE's Censo anual."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

_THOUSANDTH = Decimal("0.001")


def education_percentage(higher: int, total: int) -> Decimal | None:
    """The percentage of the `total` population (aged 15 or over) that has higher education, to
    three decimals, halves rounded up as the column stores them (numeric(6, 3)): a value that did
    not equal its stored self would be stored again on every load.

    None when `total` is 0, there is no population to share. A count that is negative, or a
    `higher` above `total`, is a broken file and raises ValueError instead of becoming a number."""
    if higher < 0 or higher > total:  # a negative total is below any valid count
        raise ValueError(f"{higher} with higher education out of {total}")
    if total == 0:
        return None
    return (Decimal(higher) * 100 / Decimal(total)).quantize(_THOUSANDTH, rounding=ROUND_HALF_UP)


class EducationLevel(StrEnum):
    TOTAL = "total"  # every level: the population the percentage is of
    HIGHER = "higher"  # "Educación superior"


@dataclass(frozen=True, slots=True)
class EducationCount:
    """People of one municipality and year at one level, as a file of the INE counts them."""

    municipality_code: str  # INE: province (2) + municipality (3)
    level: EducationLevel
    count: int
