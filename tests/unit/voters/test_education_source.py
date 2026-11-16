import hashlib
from pathlib import Path

import pytest

from datos.voters.domain.education import EducationCount, EducationLevel
from datos.voters.infrastructure.education_source import (
    EducationFile,
    InvalidEducationFileError,
    education_count,
    read_education_file,
)


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


FIXTURES = Path(__file__).parents[2] / "fixtures" / "ine"
BIG = FIXTURES / "education-66620-sample.csv"  # municipalities of 500 people or more, with ages
SMALL = FIXTURES / "education-66623-sample.csv"  # 50 to 499, without the age column


def _by_municipality(file: EducationFile) -> dict[tuple[str, EducationLevel], int]:
    return {(c.municipality_code, c.level): c.count for c in file.counts}


def test_the_file_with_ages_gives_the_counts_of_15_or_more_in_the_year() -> None:
    file = read_education_file(BIG, 2023)

    assert _by_municipality(file) == {
        ("01001", EducationLevel.TOTAL): 2452,
        ("01001", EducationLevel.HIGHER): 1055,
        ("28079", EducationLevel.TOTAL): 2_925_135,
        ("28079", EducationLevel.HIGHER): 1_354_780,
    }


def test_the_file_without_ages_gives_its_counts_the_same_way() -> None:
    file = read_education_file(SMALL, 2023)

    assert _by_municipality(file) == {
        ("01006", EducationLevel.TOTAL): 207,
        ("01006", EducationLevel.HIGHER): 84,
        ("01011", EducationLevel.TOTAL): 278,
        ("01011", EducationLevel.HIGHER): 83,
    }


def test_the_year_chooses_the_rows() -> None:
    counts = _by_municipality(read_education_file(SMALL, 2021))

    assert counts[("01006", EducationLevel.TOTAL)] == 198


def test_the_hash_and_the_name_are_those_of_the_file_as_it_is() -> None:
    file = read_education_file(SMALL, 2023)

    assert file.sha256 == hashlib.sha256(SMALL.read_bytes()).hexdigest()
    assert file.source_file == "education-66623-sample.csv"


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "table.csv"
    path.write_bytes(text.encode("utf-8"))
    return path


HEADER = "Municipios;Sexo;Nivel de estudios;Periodo;Total\r\n"


def test_a_file_without_the_bom_and_with_a_blank_line_at_the_end_is_read(tmp_path: Path) -> None:
    text = HEADER + "01006 Armiñón;Total;Total;2023;207\r\n\r\n"

    file = read_education_file(_write(tmp_path, text), 2023)

    assert file.counts == (EducationCount("01006", EducationLevel.TOTAL, 207),)


@pytest.mark.parametrize(
    "header",
    [
        "Municipios;Sexo;Nivel de estudios;Periodo\r\n",  # no count column
        "Municipios;Sexo;Nivel de estudios;Periodo;Total;Otra\r\n",  # a column nobody expects
        "Municipios;Nivel de estudios;Periodo;Total\r\n",  # no sex column
    ],
)
def test_a_table_with_other_columns_is_refused(tmp_path: Path, header: str) -> None:
    with pytest.raises(InvalidEducationFileError, match="unexpected columns"):
        read_education_file(_write(tmp_path, header), 2023)


def test_a_row_with_a_missing_cell_is_refused(tmp_path: Path) -> None:
    text = HEADER + "01006 Armiñón;Total;Total;2023\r\n"

    with pytest.raises(InvalidEducationFileError, match="cells"):
        read_education_file(_write(tmp_path, text), 2023)


def test_an_empty_file_is_refused(tmp_path: Path) -> None:
    with pytest.raises(InvalidEducationFileError, match="unexpected columns"):
        read_education_file(_write(tmp_path, ""), 2023)
