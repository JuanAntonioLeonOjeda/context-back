"""A municipality's share: how many of its people are of one kind, as a percentage.

Education (higher education), age (70 or over) and place of birth (born abroad) are the same
figure read from different columns of the INE's Censo anual tables: a part over a total, both
counted for the same municipality and year. What the part is, is the reader's business; this
module only turns two counts into a percentage and says what is wrong with them.
"""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from datos.voters.domain.municipal_value import MunicipalValue

_THOUSANDTH = Decimal("0.001")


def share_percentage(part: int, total: int) -> Decimal | None:
    """The percentage of the `total` population that is the `part`, to three decimals, halves
    rounded up as the column stores them (numeric(6, 3)): a value that did not equal its stored
    self would be stored again on every load.

    None when `total` is 0, there is no population to share. A count that is negative, or a
    `part` above `total`, is a broken file and raises ValueError instead of becoming a number."""
    if part < 0 or part > total:  # a negative total is below any valid count
        raise ValueError(f"{part} out of {total}: the part cannot be more than the whole")
    if total == 0:
        return None
    return (Decimal(part) * 100 / Decimal(total)).quantize(_THOUSANDTH, rounding=ROUND_HALF_UP)


class Component(StrEnum):
    TOTAL = "total"  # everybody the percentage is of
    PART = "part"  # the people of the kind the dimension measures


@dataclass(frozen=True, slots=True)
class ShareCount:
    """People of one municipality and year, in the total or in the part, as a file of the INE counts
    them."""

    municipality_code: str  # INE: province (2) + municipality (3)
    component: Component
    count: int


def share_values(counts: Sequence[ShareCount], year: int) -> tuple[list[MunicipalValue], list[str]]:
    """The percentage of every municipality, by code, and the problems of the counts (empty when
    sound). A municipality is a problem when a count is repeated (it is in two files, or twice in
    one), when it has one of the two counts but not the other, or when its part is more than its
    total. A population of 0 is not a problem: it has no percentage and is left out, as the INE's
    secrecy leaves municipalities out of the income."""
    by_municipality: dict[str, dict[Component, int]] = defaultdict(dict)
    problems: list[str] = []
    for count in counts:
        components = by_municipality[count.municipality_code]
        if count.component in components:
            problems.append(
                f"municipality {count.municipality_code}: {count.component} is repeated"
            )
        components[count.component] = count.count
    values: list[MunicipalValue] = []
    for code in sorted(by_municipality):
        components = by_municipality[code]
        if len(components) < len(Component):
            missing = next(c for c in Component if c not in components)
            problems.append(f"municipality {code}: no {missing} count")
            continue
        try:
            percentage = share_percentage(components[Component.PART], components[Component.TOTAL])
        except ValueError as error:
            problems.append(f"municipality {code}: {error}")
            continue
        if percentage is not None:
            values.append(MunicipalValue(code, year, percentage))
    return values, problems
