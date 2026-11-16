import pytest

from datos.voters.domain.education import EducationCount, EducationLevel
from datos.voters.infrastructure.education_source import InvalidEducationFileError, education_count


def _row(**changes: str) -> dict[str, str]:
    row = {
        "municipality": "01001 Alegría-Dulantzi",
        "Sexo": "Total",
        "Edad": "15 y más años",
        "Nivel de estudios": "Educación superior",
        "Periodo": "2023",
        "Total": "2.452",
    }
    return {**row, **changes}


def test_a_row_of_the_higher_level_gives_its_count_with_the_dot_of_thousands_removed() -> None:
    assert education_count(_row(), 2023) == EducationCount("01001", EducationLevel.HIGHER, 2452)


def test_the_row_of_all_levels_gives_the_total() -> None:
    row = _row(**{"Nivel de estudios": "Total", "Total": "215"})
    assert education_count(row, 2023) == EducationCount("01001", EducationLevel.TOTAL, 215)


def test_the_file_without_an_age_column_is_read_the_same() -> None:
    row = _row()
    del row["Edad"]
    assert education_count(row, 2023) == EducationCount("01001", EducationLevel.HIGHER, 2452)


@pytest.mark.parametrize(
    "changes",
    [
        {"Sexo": "Hombres"},
        {"Sexo": "Mujeres"},
        {"Edad": "De 16 a 24 años"},
        {"Periodo": "2022"},
        {"Nivel de estudios": "Educación primaria e inferior"},
    ],
)
def test_a_row_the_percentage_does_not_use_gives_nothing(changes: dict[str, str]) -> None:
    assert education_count(_row(**changes), 2023) is None


@pytest.mark.parametrize("cell", ["Alegría", "1001 Alegría", "010011 Alegría", "01001"])
def test_a_municipality_without_its_code_is_refused(cell: str) -> None:
    with pytest.raises(InvalidEducationFileError, match="municipality"):
        education_count(_row(municipality=cell), 2023)


@pytest.mark.parametrize("cell", ["", "1,5", "12.34", ".5", "1.2345", "-3", "n/d"])
def test_a_count_that_is_not_a_whole_number_is_refused(cell: str) -> None:
    with pytest.raises(InvalidEducationFileError, match="whole number"):
        education_count(_row(Total=cell), 2023)


def test_an_unreadable_row_that_the_percentage_does_not_use_is_not_an_error() -> None:
    assert education_count(_row(Sexo="Hombres", Total="n/d"), 2023) is None
