"""Share of a municipality's population with higher education, from the INE's Censo anual."""

from decimal import ROUND_HALF_UP, Decimal

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
