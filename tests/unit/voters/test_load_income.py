"""Loading a year's income: checks, and what is stored and what is not."""

from collections.abc import Sequence
from decimal import Decimal

import pytest

from datos.voters.application.load_income import (
    IncomeDownload,
    InvalidIncomeError,
    load_income,
)
from datos.voters.domain.income import MunicipalIncome

PROVINCES = {"prov-02", "prov-35"}


def _income(code: str, euros: str) -> MunicipalIncome:
    return MunicipalIncome(code, 2023, Decimal(euros), f"ADRH-{code}")


class _Source:
    def __init__(self, incomes: list[MunicipalIncome]) -> None:
        self._incomes = incomes

    def incomes(self, year: int) -> IncomeDownload:
        return IncomeDownload("https://servicios.ine.es/...", "0" * 64, self._incomes)


class _Repository:
    def __init__(self, stored: dict[str, Decimal] | None = None) -> None:
        self.stored = stored or {}
        self.recorded: list[list[str]] = []

    def province_ids(self) -> set[str]:
        return set(PROVINCES)

    def latest_incomes(self, year: int) -> dict[str, Decimal]:
        return dict(self.stored)

    def record(self, download: IncomeDownload, incomes: Sequence[MunicipalIncome]) -> None:
        self.recorded.append([i.municipality_code for i in incomes])


def test_stores_every_new_income_in_one_go() -> None:
    repository = _Repository()

    stored = load_income(
        _Source([_income("02003", "14611"), _income("35016", "13000")]), repository, year=2023
    )

    assert stored == 2
    assert repository.recorded == [["02003", "35016"]]


def test_an_unchanged_value_is_not_stored_again_and_a_revised_one_is() -> None:
    repository = _Repository(stored={"02003": Decimal("14611"), "35016": Decimal("12900")})

    stored = load_income(
        _Source([_income("02003", "14611"), _income("35016", "13000")]), repository, year=2023
    )

    assert stored == 1
    assert repository.recorded == [["35016"]]


def test_nothing_new_records_no_download() -> None:
    repository = _Repository(stored={"02003": Decimal("14611")})

    assert load_income(_Source([_income("02003", "14611")]), repository, year=2023) == 0
    assert repository.recorded == []


@pytest.mark.parametrize(
    ("incomes", "problem"),
    [
        ([_income("02003", "1"), _income("02003", "2")], "02003 is repeated"),
        ([_income("99001", "100")], "99001: unknown province"),
        ([_income("02003", "0")], "02003: income 0"),
    ],
)
def test_an_unsound_answer_writes_nothing(incomes: list[MunicipalIncome], problem: str) -> None:
    repository = _Repository()

    with pytest.raises(InvalidIncomeError, match=problem):
        load_income(_Source(incomes), repository, year=2023)
    assert repository.recorded == []
