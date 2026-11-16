import hashlib
from pathlib import Path

import pytest

from datos.voters.domain.share import Component, ShareCount
from datos.voters.infrastructure.table_source import (
    CategoryCount,
    InvalidTableFileError,
    TableLayout,
    category_count,
    read_table_file,
)

EDUCATION = TableLayout(
    category="Nivel de estudios",
    total="Total",
    part=frozenset({"Educación superior"}),
    fixed={"Sexo": "Total", "Edad": "15 y más años"},
    optional=frozenset({"Edad"}),
)
AGE = TableLayout(
    category="Edad",
    total="15 y más años",
    part=frozenset({"De 70 a 79 años", "De 80 a 89 años", "90 y más años"}),
    fixed={"Sexo": "Total", "Nivel de estudios": "Total"},
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


def test_a_row_of_the_part_gives_its_count_with_the_dot_of_thousands_removed() -> None:
    assert category_count(EDUCATION, _row(), 2023) == CategoryCount(
        "01001", "Educación superior", 2452
    )


def test_the_row_of_the_whole_gives_its_count() -> None:
    row = _row(**{"Nivel de estudios": "Total", "Total": "215"})
    assert category_count(EDUCATION, row, 2023) == CategoryCount("01001", "Total", 215)


def test_a_pinned_column_the_file_may_lack_is_not_asked_for() -> None:
    row = _row()
    del row["Edad"]
    assert category_count(EDUCATION, row, 2023) == CategoryCount(
        "01001", "Educación superior", 2452
    )


def test_a_pinned_column_the_file_must_have_is_asked_for() -> None:
    row = _row()
    del row["Sexo"]
    with pytest.raises(KeyError):
        category_count(EDUCATION, row, 2023)


@pytest.mark.parametrize(
    "changes",
    [
        {"Sexo": "Hombres"},
        {"Edad": "De 16 a 24 años"},
        {"Periodo": "2022"},
        {"Nivel de estudios": "Educación primaria e inferior"},
    ],
)
def test_a_row_the_share_does_not_use_gives_nothing(changes: dict[str, str]) -> None:
    assert category_count(EDUCATION, _row(**changes), 2023) is None


def test_every_value_of_a_part_made_of_several_gives_its_own_count() -> None:
    row = _row(Edad="De 80 a 89 años", **{"Nivel de estudios": "Total", "Total": "130"})
    assert category_count(AGE, row, 2023) == CategoryCount("01001", "De 80 a 89 años", 130)


def test_an_age_group_that_is_not_in_the_part_gives_nothing() -> None:
    row = _row(Edad="De 60 a 69 años", **{"Nivel de estudios": "Total"})
    assert category_count(AGE, row, 2023) is None


@pytest.mark.parametrize("cell", ["Alegría", "1001 Alegría", "010011 Alegría", "01001"])
def test_a_municipality_without_its_code_is_refused(cell: str) -> None:
    with pytest.raises(InvalidTableFileError, match="municipality"):
        category_count(EDUCATION, _row(municipality=cell), 2023)


@pytest.mark.parametrize("cell", ["", "1,5", "12.34", ".5", "1.2345", "-3", "n/d"])
def test_a_count_that_is_not_a_whole_number_is_refused(cell: str) -> None:
    with pytest.raises(InvalidTableFileError, match="whole number"):
        category_count(EDUCATION, _row(Total=cell), 2023)


def test_an_unreadable_row_that_the_share_does_not_use_is_not_an_error() -> None:
    assert category_count(EDUCATION, _row(Sexo="Hombres", Total="n/d"), 2023) is None


@pytest.mark.parametrize(
    "layout",
    [
        {"part": frozenset()},  # no part
        {"part": frozenset({"Total"})},  # the whole is also the part
        {"fixed": {"Nivel de estudios": "Total"}},  # the category is pinned too
        {"optional": frozenset({"Otra"})},  # optional but not pinned
    ],
)
def test_a_layout_that_cannot_give_a_share_is_refused_when_it_is_written(
    layout: dict[str, object],
) -> None:
    arguments: dict[str, object] = {
        "category": "Nivel de estudios",
        "total": "Total",
        "part": frozenset({"Educación superior"}),
        "fixed": {"Sexo": "Total"},
        **layout,
    }
    with pytest.raises(ValueError, match="layout"):
        TableLayout(**arguments)  # type: ignore[arg-type]  # the arguments are built from a dict


# --- the file ---------------------------------------------------------------------------------

HEADER = "Municipios;Sexo;Edad;Nivel de estudios;Periodo;Total\r\n"
URL = "https://www.ine.es/jaxiT3/Tabla.htm?t=66620"
AGES = ("15 y más años", "De 70 a 79 años", "De 80 a 89 años", "90 y más años")


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "table.csv"
    path.write_bytes(text.encode("utf-8"))
    return path


def _age_rows(code: str, counts: tuple[int, ...], ages: tuple[str, ...] = AGES) -> str:
    return "".join(
        f"{code} Sitio;Total;{age};Total;2023;{count}\r\n"
        for age, count in zip(ages, counts, strict=True)
    )


def test_a_part_of_several_values_is_the_sum_of_them(tmp_path: Path) -> None:
    text = HEADER + _age_rows("01001", (1000, 100, 40, 10))

    file = read_table_file(_write(tmp_path, text), 2023, AGE, source_url=URL)

    assert file.counts == [
        ShareCount("01001", Component.TOTAL, 1000),
        ShareCount("01001", Component.PART, 150),
    ]


def test_the_counts_come_sorted_by_municipality(tmp_path: Path) -> None:
    text = HEADER + _age_rows("28079", (9, 3, 2, 1)) + _age_rows("01001", (5, 2, 1, 1))

    file = read_table_file(_write(tmp_path, text), 2023, AGE, source_url=URL)

    assert [c.municipality_code for c in file.counts] == ["01001", "01001", "28079", "28079"]


def test_a_municipality_with_some_values_of_the_part_but_not_all_is_refused(tmp_path: Path) -> None:
    text = HEADER + _age_rows(
        "01001", (1000, 100, 10), ("15 y más años", "De 70 a 79 años", "90 y más años")
    )

    with pytest.raises(InvalidTableFileError, match=r"01001.*De 80 a 89 años"):
        read_table_file(_write(tmp_path, text), 2023, AGE, source_url=URL)


def test_a_value_repeated_for_a_municipality_is_refused(tmp_path: Path) -> None:
    text = HEADER + _age_rows("01001", (1000, 100, 40, 10)) + _age_rows("01001", (1, 1, 1, 1))

    with pytest.raises(InvalidTableFileError, match=r"01001.*repeated"):
        read_table_file(_write(tmp_path, text), 2023, AGE, source_url=URL)


def test_a_municipality_without_any_value_of_the_part_gives_only_its_total(tmp_path: Path) -> None:
    text = HEADER + _age_rows("01001", (1000,), ("15 y más años",))

    file = read_table_file(_write(tmp_path, text), 2023, AGE, source_url=URL)

    assert file.counts == [ShareCount("01001", Component.TOTAL, 1000)]


def test_the_hash_and_the_name_are_those_of_the_file_as_it_is(tmp_path: Path) -> None:
    path = _write(tmp_path, HEADER + _age_rows("01001", (1000, 100, 40, 10)))

    file = read_table_file(path, 2023, AGE, source_url=URL)

    assert file.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert (file.source_file, file.source_url) == ("table.csv", URL)


def test_a_file_with_the_bom_and_a_blank_line_at_the_end_is_read(tmp_path: Path) -> None:
    text = "﻿" + HEADER + _age_rows("01001", (1000, 100, 40, 10)) + "\r\n"

    file = read_table_file(_write(tmp_path, text), 2023, AGE, source_url=URL)

    assert len(file.counts) == 2


def test_the_file_without_an_optional_column_is_read_with_the_same_layout(tmp_path: Path) -> None:
    text = (
        "Municipios;Sexo;Nivel de estudios;Periodo;Total\r\n"
        "01006 Armiñón;Total;Total;2023;207\r\n"
        "01006 Armiñón;Total;Educación superior;2023;84\r\n"
    )

    file = read_table_file(_write(tmp_path, text), 2023, EDUCATION, source_url=URL)

    assert file.counts == [
        ShareCount("01006", Component.TOTAL, 207),
        ShareCount("01006", Component.PART, 84),
    ]


@pytest.mark.parametrize(
    "header",
    [
        "Municipios;Sexo;Nivel de estudios;Periodo\r\n",  # no count column
        "Municipios;Sexo;Edad;Nivel de estudios;Periodo;Total;Otra\r\n",  # a column nobody expects
        "Municipios;Edad;Nivel de estudios;Periodo;Total\r\n",  # a pinned column is missing
        "Municipios;Sexo;Nivel de estudios;Periodo;Total\r\n",  # the category column is missing
        "",
    ],
)
def test_a_table_with_other_columns_than_the_layout_is_refused(tmp_path: Path, header: str) -> None:
    with pytest.raises(InvalidTableFileError, match="unexpected columns"):
        read_table_file(_write(tmp_path, header), 2023, AGE, source_url=URL)


def test_a_row_with_a_missing_cell_is_refused(tmp_path: Path) -> None:
    text = HEADER + "01001 Sitio;Total;15 y más años;Total;2023\r\n"

    with pytest.raises(InvalidTableFileError, match="cells"):
        read_table_file(_write(tmp_path, text), 2023, AGE, source_url=URL)


def test_a_file_that_is_not_utf_8_is_refused_with_its_name(tmp_path: Path) -> None:
    path = tmp_path / "table.csv"
    path.write_bytes(
        HEADER.encode() + "01006 Armi\xf1\xf3n;Total;x;Total;2023;1\r\n".encode("latin-1")
    )

    with pytest.raises(InvalidTableFileError, match=r"table\.csv"):
        read_table_file(path, 2023, AGE, source_url=URL)


def test_a_file_that_does_not_exist_is_refused_with_its_name(tmp_path: Path) -> None:
    with pytest.raises(InvalidTableFileError, match=r"missing\.csv"):
        read_table_file(tmp_path / "missing.csv", 2023, AGE, source_url=URL)


def test_a_field_too_long_to_be_csv_is_refused(tmp_path: Path) -> None:
    text = HEADER + "01006 " + "x" * 200_000 + ";Total;x;Total;2023;1\r\n"

    with pytest.raises(InvalidTableFileError, match=r"table\.csv"):
        read_table_file(_write(tmp_path, text), 2023, AGE, source_url=URL)


def test_a_municipality_without_its_total_gives_only_its_part(tmp_path: Path) -> None:
    text = HEADER + _age_rows(
        "01001", (100, 40, 10), ("De 70 a 79 años", "De 80 a 89 años", "90 y más años")
    )

    file = read_table_file(_write(tmp_path, text), 2023, AGE, source_url=URL)

    assert file.counts == [ShareCount("01001", Component.PART, 150)]
