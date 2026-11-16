import pytest

from datos.voters.infrastructure.table_source import (
    CategoryCount,
    InvalidTableFileError,
    TableLayout,
    category_count,
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
