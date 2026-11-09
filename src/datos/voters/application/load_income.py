"""Load the mean net income per person of every municipality for a year (spec AC2)."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from datos.voters.domain.income import MunicipalIncome, changed_since, income_problems


@dataclass(frozen=True, slots=True)
class IncomeDownload:
    """One response of the INE with every municipality's income for a year."""

    url: str
    sha256: str
    incomes: Sequence[MunicipalIncome]


class IncomeSource(Protocol):
    def incomes(self, year: int) -> IncomeDownload: ...


class IncomeRepository(Protocol):
    def province_ids(self) -> set[str]: ...

    def latest_incomes(self, year: int) -> dict[str, Decimal]:
        """The latest stored value of every municipality for the year."""
        ...

    def record(self, download: IncomeDownload, incomes: Sequence[MunicipalIncome]) -> None:
        """Store the download and these incomes in one transaction."""
        ...


class InvalidIncomeError(Exception):
    def __init__(self, problems: Sequence[str]) -> None:
        super().__init__(f"{len(problems)} problem(s):\n- " + "\n- ".join(problems))
        self.problems = list(problems)


def load_income(source: IncomeSource, repository: IncomeRepository, *, year: int) -> int:
    """Check the year's incomes and store the new or revised ones; returns how many.

    An unchanged value is not stored again, and a download with nothing new is not recorded.
    """
    download = source.incomes(year)
    problems = income_problems(download.incomes, repository.province_ids())
    if problems:
        raise InvalidIncomeError(problems)
    changed = changed_since(download.incomes, repository.latest_incomes(year))
    if changed:
        repository.record(download, changed)
    return len(changed)
