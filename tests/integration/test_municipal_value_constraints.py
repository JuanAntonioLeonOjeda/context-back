"""The rules migration 0017 promises for the municipal values of a dimension, on PostgreSQL."""

from collections.abc import Callable

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError

pytestmark = pytest.mark.integration

SHA = "1" * 64
URL = "https://www.ine.es/jaxiT3/Tabla.htm?t=66620"


@pytest.fixture
def seeded(db: Connection) -> Connection:
    db.execute(
        text(
            "INSERT INTO territories (id, ine_code, name, level, parent_id) VALUES"
            " ('es', NULL, 'España', 'state', NULL),"
            " ('ccaa-05', '05', 'Canarias', 'ccaa', 'es'),"
            " ('prov-35', '35', 'Las Palmas', 'province', 'ccaa-05')"
        )
    )
    return db


def _load(db: Connection, *, sha: str = SHA, dimension: str = "education") -> int:
    load_id = db.execute(
        text(
            "INSERT INTO municipal_value_loads (dimension, source_url, source_file, source_sha256)"
            " VALUES (:dimension, :url, '66620.csv', :sha) RETURNING id"
        ),
        {"dimension": dimension, "url": URL, "sha": sha},
    ).scalar_one()
    return int(load_id)


def _value(
    db: Connection, load: int, code: str = "35016", *, year: int = 2023, value: str = "33.1"
) -> None:
    db.execute(
        text(
            "INSERT INTO municipal_values (load_id, municipality_code, year, value)"
            " VALUES (:load, :code, :year, :value)"
        ),
        {"load": load, "code": code, "year": year, "value": value},
    )


def _bad_value(
    db: Connection, *, code: str = "35016", year: int = 2023, value: str = "33.1"
) -> None:
    """A value on a load of its own, valid in everything but what the caller changes."""
    _value(db, _load(db, sha="2" * 64), code, year=year, value=value)


def _refused(db: Connection, constraint: str, attempt: Callable[[], object]) -> None:
    """Runs `attempt` in a savepoint and checks the database refused it by that constraint."""
    with pytest.raises(DBAPIError) as error, db.begin_nested():
        attempt()
    assert constraint in str(error.value)


def test_a_value_is_stored_with_its_province(seeded: Connection) -> None:
    _value(seeded, _load(seeded))

    province = seeded.execute(text("SELECT province_id FROM municipal_values")).scalar_one()
    assert province == "prov-35"


def test_a_municipality_of_an_unknown_province_is_refused(seeded: Connection) -> None:
    with pytest.raises(DBAPIError) as error, seeded.begin_nested():
        _value(seeded, _load(seeded), "99001")
    assert "province_id" in str(error.value)


def test_a_municipality_code_must_have_five_digits(seeded: Connection) -> None:
    _refused(seeded, "municipal_values_code_5_digits", lambda: _bad_value(seeded, code="3501"))


def test_a_year_outside_the_plausible_range_is_refused(seeded: Connection) -> None:
    _refused(seeded, "municipal_values_year_plausible", lambda: _bad_value(seeded, year=1999))


@pytest.mark.parametrize("value", ["-0.001", "100.001"])
def test_a_percentage_outside_0_and_100_is_refused(seeded: Connection, value: str) -> None:
    _refused(seeded, "municipal_values_percent", lambda: _bad_value(seeded, value=value))


@pytest.mark.parametrize("value", ["0", "100"])
def test_the_limits_of_the_percentage_are_stored(seeded: Connection, value: str) -> None:
    _value(seeded, _load(seeded), value=value)


def test_a_municipality_has_one_value_per_load_and_year(seeded: Connection) -> None:
    load = _load(seeded)
    _value(seeded, load)
    with pytest.raises(DBAPIError) as error, seeded.begin_nested():
        _value(seeded, load)
    assert "municipal_values_pkey" in str(error.value)


def test_a_new_load_may_revise_the_same_value(seeded: Connection) -> None:
    _value(seeded, _load(seeded), value="33.1")
    _value(seeded, _load(seeded, sha="3" * 64), value="33.4")

    count = seeded.execute(text("SELECT count(*) FROM municipal_values")).scalar_one()
    assert count == 2


def test_the_same_file_cannot_be_loaded_twice(seeded: Connection) -> None:
    _load(seeded)
    _refused(seeded, "municipal_value_loads_one_file", lambda: _load(seeded))


def test_a_dimension_the_code_does_not_know_is_refused(seeded: Connection) -> None:
    _refused(
        seeded,
        "municipal_value_loads_dimension_known",
        lambda: _load(seeded, dimension="astrology"),
    )


def test_a_hash_must_be_64_hex_digits(seeded: Connection) -> None:
    _refused(seeded, "municipal_value_loads_sha256_hex", lambda: _load(seeded, sha="XYZ"))


def test_a_value_of_a_load_that_does_not_exist_is_refused(seeded: Connection) -> None:
    with pytest.raises(DBAPIError) as error, seeded.begin_nested():
        _value(seeded, 424242)
    assert "municipal_values_load_id_fkey" in str(error.value)


@pytest.fixture
def stored(seeded: Connection) -> Connection:
    _value(seeded, _load(seeded))
    return seeded


# Each append-only table with a column an UPDATE can name.
APPEND_ONLY = {"municipal_value_loads": "source_file", "municipal_values": "year"}


@pytest.mark.parametrize("table", APPEND_ONLY)
@pytest.mark.parametrize(
    ("statement", "operation"),
    [
        ("UPDATE {table} SET {column} = {column}", "UPDATE"),
        ("DELETE FROM {table}", "DELETE"),
        ("TRUNCATE {table} CASCADE", "TRUNCATE"),
    ],
)
def test_nothing_stored_can_be_changed_or_removed(
    stored: Connection, table: str, statement: str, operation: str
) -> None:
    with pytest.raises(DBAPIError) as error, stored.begin_nested():
        stored.execute(text(statement.format(table=table, column=APPEND_ONLY[table])))
    assert f"{table} is append-only: {operation} is not allowed" in str(error.value)
