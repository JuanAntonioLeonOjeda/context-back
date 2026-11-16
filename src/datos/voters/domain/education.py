"""Share of a municipality's population with higher education, from the INE's Censo anual."""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from datos.voters.domain.municipal_value import MunicipalValue

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


def education_values(
    counts: Sequence[EducationCount], year: int
) -> tuple[list[MunicipalValue], list[str]]:
    """The percentage of every municipality, by code, and the problems of the counts (empty when
    sound). A municipality is a problem when a count is repeated (it is in two files, or twice in
    one), when it has one of the two counts but not the other, or when it has more people with
    higher education than people. A population of 0 is not a problem: it has no percentage and is
    left out, as the INE's secrecy leaves municipalities out of the income."""
    by_municipality: dict[str, dict[EducationLevel, int]] = defaultdict(dict)
    problems: list[str] = []
    for count in counts:
        levels = by_municipality[count.municipality_code]
        if count.level in levels:
            problems.append(f"municipality {count.municipality_code}: {count.level} is repeated")
        levels[count.level] = count.count
    values: list[MunicipalValue] = []
    for code in sorted(by_municipality):
        levels = by_municipality[code]
        if len(levels) < len(EducationLevel):
            missing = next(level for level in EducationLevel if level not in levels)
            problems.append(f"municipality {code}: no {missing} count")
            continue
        try:
            percentage = education_percentage(
                levels[EducationLevel.HIGHER], levels[EducationLevel.TOTAL]
            )
        except ValueError as error:
            problems.append(f"municipality {code}: {error}")
            continue
        if percentage is not None:
            values.append(MunicipalValue(code, year, percentage))
    return values, problems
