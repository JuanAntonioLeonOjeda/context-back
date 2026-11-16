"""Loading a year's education percentages: checks, and what is stored and what is not."""

from collections.abc import Sequence
from decimal import Decimal

import pytest

from datos.voters.application.load_education import (
    EDUCATION,
    EducationSourceFile,
    InvalidValuesError,
    ValueLoad,
    load_education,
)
from datos.voters.domain.share import Component, ShareCount


class FakeValueRepository:
    def __init__(self, stored: dict[str, Decimal] | None = None) -> None:
        self.stored = stored or {}
        self.recorded: list[tuple[str, Sequence[ValueLoad]]] = []

    def province_ids(self) -> set[str]:
        return {"prov-01", "prov-28"}

    def latest_values(self, dimension: str, year: int) -> dict[str, Decimal]:
        assert (dimension, year) == (EDUCATION, 2023)
        return self.stored

    def record(self, dimension: str, loads: Sequence[ValueLoad]) -> None:
        self.recorded.append((dimension, loads))


def _file(name: str, *municipalities: tuple[str, int, int]) -> EducationSourceFile:
    counts = [
        count
        for code, higher, total in municipalities
        for count in (
            ShareCount(code, Component.TOTAL, total),
            ShareCount(code, Component.PART, higher),
        )
    ]
    return EducationSourceFile(f"https://ine.es/{name}", f"{name}.csv", name[0] * 64, counts)


BIG = _file("big", ("28079", 1_354_780, 2_925_135))  # 46.315
SMALL = _file("small", ("01006", 84, 207))  # 40.580


def test_every_value_is_stored_in_the_load_of_the_file_it_came_from() -> None:
    repository = FakeValueRepository()

    stored = load_education([BIG, SMALL], repository, year=2023)

    assert stored == 2
    [(dimension, loads)] = repository.recorded
    assert dimension == "education"
    assert [
        (load.source_file, [(v.municipality_code, v.value) for v in load.values]) for load in loads
    ] == [
        ("big.csv", [("28079", Decimal("46.315"))]),
        ("small.csv", [("01006", Decimal("40.580"))]),
    ]
    assert loads[0].source_url == "https://ine.es/big"
    assert loads[0].sha256 == "b" * 64


def test_an_unchanged_value_is_not_stored_again_and_nothing_is_recorded() -> None:
    repository = FakeValueRepository({"28079": Decimal("46.315"), "01006": Decimal("40.580")})

    assert load_education([BIG, SMALL], repository, year=2023) == 0
    assert repository.recorded == []


def test_only_the_revised_value_is_stored_and_only_in_its_file() -> None:
    repository = FakeValueRepository({"28079": Decimal("46.315"), "01006": Decimal("40.000")})

    assert load_education([BIG, SMALL], repository, year=2023) == 1
    [(_, loads)] = repository.recorded
    assert [load.source_file for load in loads] == ["small.csv"]  # BIG has nothing new


def test_files_without_counts_of_the_year_are_refused_instead_of_storing_nothing() -> None:
    empty = EducationSourceFile("https://ine.es/e", "e.csv", "e" * 64, [])

    with pytest.raises(InvalidValuesError, match=r"e\.csv: no education count"):
        load_education([empty], FakeValueRepository(), year=2023)


def test_a_file_without_counts_is_refused_even_when_the_other_has_them() -> None:
    wrong_year = EducationSourceFile("https://ine.es/w", "w.csv", "w" * 64, [])
    repository = FakeValueRepository()

    with pytest.raises(InvalidValuesError) as error:
        load_education([BIG, wrong_year], repository, year=2023)

    assert error.value.problems == ["w.csv: no education count of any municipality for 2023"]
    assert repository.recorded == []


def test_a_municipality_of_an_unknown_province_is_refused_and_nothing_is_recorded() -> None:
    repository = FakeValueRepository()
    elsewhere = _file("else", ("99001", 1, 2))

    with pytest.raises(InvalidValuesError) as error:
        load_education([BIG, elsewhere], repository, year=2023)

    assert error.value.problems == ["municipality 99001: unknown province"]
    assert repository.recorded == []


def test_the_problems_of_the_counts_and_of_the_provinces_come_together() -> None:
    broken = _file("broken", ("01006", 300, 207), ("99001", 1, 2))

    with pytest.raises(InvalidValuesError) as error:
        load_education([broken], FakeValueRepository(), year=2023)

    assert len(error.value.problems) == 2


def test_a_municipality_in_two_files_is_refused() -> None:
    with pytest.raises(InvalidValuesError, match="repeated"):
        load_education(
            [SMALL, _file("again", ("01006", 84, 207))], FakeValueRepository(), year=2023
        )
