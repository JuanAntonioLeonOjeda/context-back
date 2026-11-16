"""Municipal values stored with the load of their file; the latest load wins; nothing is
overwritten, and a refused load leaves nothing behind."""

from decimal import Decimal

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from datos.voters.application.load_education import (
    EDUCATION,
    EducationSourceFile,
    ValueLoad,
    load_education,
)
from datos.voters.domain.education import EducationCount, EducationLevel
from datos.voters.domain.municipal_value import MunicipalValue
from datos.voters.infrastructure.pg_value_repository import PgValueRepository

pytestmark = pytest.mark.integration


def _load(sha: str, *values: tuple[str, str], year: int = 2023) -> ValueLoad:
    return ValueLoad(
        "https://www.ine.es/jaxiT3/Tabla.htm?t=66620",
        "66620.csv",
        sha * 64,
        [MunicipalValue(code, year, Decimal(value)) for code, value in values],
    )


def _stored(engine: Engine) -> list[tuple[object, ...]]:
    with engine.connect() as connection:
        return [
            tuple(r)
            for r in connection.execute(
                text(
                    "SELECT v.municipality_code, v.province_id, v.value, l.dimension, l.source_file"
                    " FROM municipal_values v JOIN municipal_value_loads l ON l.id = v.load_id"
                    " ORDER BY v.load_id, v.municipality_code"
                )
            )
        ]


def test_a_load_is_stored_with_its_province_and_its_file(engine: Engine) -> None:
    PgValueRepository(engine).record(EDUCATION, [_load("a", ("28079", "46.315"))])

    assert _stored(engine) == [
        ("28079", "prov-28", Decimal("46.315"), "education", "66620.csv"),
    ]


def test_the_latest_load_wins_and_the_first_stays(engine: Engine) -> None:
    repository = PgValueRepository(engine)
    repository.record(EDUCATION, [_load("a", ("28079", "46.315"), ("01006", "40.580"))])
    repository.record(EDUCATION, [_load("b", ("28079", "46.400"))])

    assert repository.latest_values(EDUCATION, 2023) == {
        "28079": Decimal("46.400"),
        "01006": Decimal("40.580"),
    }
    assert len(_stored(engine)) == 3  # the revision is a new row, nothing was overwritten


def test_the_latest_values_are_those_of_the_year_and_the_dimension_asked(engine: Engine) -> None:
    repository = PgValueRepository(engine)
    repository.record(
        EDUCATION, [_load("a", ("28079", "46.315")), _load("b", ("01006", "40"), year=2022)]
    )

    assert repository.latest_values(EDUCATION, 2023) == {"28079": Decimal("46.315")}
    assert repository.latest_values("income", 2023) == {}


def test_a_refused_load_leaves_nothing_of_the_others_in_its_call(engine: Engine) -> None:
    repository = PgValueRepository(engine)
    repository.record(EDUCATION, [_load("a", ("28079", "46.315"))])

    # The second load is refused for its value (a percentage above 100): the first one of the same
    # call must not stay.
    with pytest.raises(DBAPIError, match="municipal_values_percent"):
        repository.record(
            EDUCATION, [_load("b", ("01006", "40.580")), _load("c", ("28079", "101"))]
        )

    assert repository.latest_values(EDUCATION, 2023) == {"28079": Decimal("46.315")}


def test_the_provinces_are_the_ones_of_the_territories(engine: Engine) -> None:
    provinces = PgValueRepository(engine).province_ids()

    assert {"prov-01", "prov-28", "prov-35"} <= provinces
    assert "ccaa-13" not in provinces


def _file(sha: str, higher: int) -> EducationSourceFile:
    counts = [
        EducationCount("28079", EducationLevel.TOTAL, 1000),
        EducationCount("28079", EducationLevel.HIGHER, higher),
    ]
    return EducationSourceFile("https://www.ine.es/t", "66620.csv", sha * 64, counts)


def test_loading_the_same_file_twice_stores_nothing_the_second_time(engine: Engine) -> None:
    repository = PgValueRepository(engine)

    first = load_education([_file("a", 463)], repository, year=2023)
    second = load_education([_file("a", 463)], repository, year=2023)

    assert (first, second) == (1, 0)
    assert len(_stored(engine)) == 1


def test_a_revised_file_adds_a_row_and_becomes_the_current_value(engine: Engine) -> None:
    repository = PgValueRepository(engine)
    load_education([_file("a", 463)], repository, year=2023)

    assert load_education([_file("b", 470)], repository, year=2023) == 1
    assert repository.latest_values(EDUCATION, 2023) == {"28079": Decimal("47.000")}
