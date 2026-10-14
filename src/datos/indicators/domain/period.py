"""The period of an INE value, from the year and the INE period code (`FK_Periodo`).

Pure. Only codes verified on 2026-10-13 are accepted: 28 is the whole year and 19-22 the
four quarters. Any other code is rejected, never guessed: a monthly or half-year series
needs its codes checked and added here first.
"""

from dataclasses import dataclass
from datetime import date

ANNUAL_CODE = 28
QUARTER_CODES = {19: 1, 20: 2, 21: 3, 22: 4}


class UnknownPeriodError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Period:
    year: int
    quarter: int | None  # None for a whole year

    @property
    def start(self) -> date:
        month = 1 if self.quarter is None else 3 * (self.quarter - 1) + 1
        return date(self.year, month, 1)


def period_from_ine(year: int, code: int) -> Period:
    if code == ANNUAL_CODE:
        return Period(year, None)
    if code in QUARTER_CODES:
        return Period(year, QUARTER_CODES[code])
    raise UnknownPeriodError(f"INE period code {code} is not a known year or quarter")
