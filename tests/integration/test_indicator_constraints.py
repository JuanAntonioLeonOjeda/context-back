from datetime import date

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError

pytestmark = pytest.mark.integration

SHA = "a" * 64
INSERT_OBSERVATION = (
    "INSERT INTO observations (indicator_id, territory_id, period_year, period_code,"
    " period_start, value, source_series_code, download_id)"
    " VALUES ('unemployment_rate', 'ccaa-13', :year, :code, :start, :value, 'EPA452576',"
    " :download_id)"
)


@pytest.fixture
def seeded(db: Connection) -> Connection:
    db.execute(
        text(
            "INSERT INTO territories (id, ine_code, name, level, parent_id) VALUES"
            " ('es', NULL, 'España', 'state', NULL),"
            " ('ccaa-13', '13', 'Community A', 'ccaa', 'es')"
        )
    )
    db.execute(
        text(
            "INSERT INTO indicators (id, name, unit, scale_factor, periodicity,"
            " source_table_id, description) VALUES ('unemployment_rate', 'Tasa de paro', '%',"
            " 1, 'quarterly', '14506', 'EPA, both sexes, total')"
        )
    )
    return db


def _download(db: Connection) -> int:
    return int(
        db.execute(
            text(
                "INSERT INTO downloads (source, url, sha256) VALUES"
                " ('ine', 'https://servicios.ine.es/x', :sha) RETURNING id"
            ),
            {"sha": SHA},
        ).scalar_one()
    )


def _observe(
    db: Connection, download_id: int, value: float, *, start: date = date(2026, 4, 1)
) -> None:
    db.execute(
        text(INSERT_OBSERVATION),
        {"year": 2026, "code": 20, "start": start, "value": value, "download_id": download_id},
    )


def _rejected(db: Connection, statement: str, params: dict[str, object] | None = None) -> str:
    with pytest.raises(DBAPIError) as error, db.begin_nested():
        db.execute(text(statement), params or {})
    return str(error.value)


def test_the_current_value_is_the_one_of_the_latest_download(seeded: Connection) -> None:
    first, second = _download(seeded), _download(seeded)
    _observe(seeded, first, 14.66)
    _observe(seeded, second, 14.56)  # revised

    current = seeded.execute(text("SELECT value, download_id FROM current_observations")).one()

    assert (float(current.value), current.download_id) == (14.56, second)
    assert seeded.execute(text("SELECT count(*) FROM observations")).scalar_one() == 2


def test_a_value_can_come_back_after_a_revision(seeded: Connection) -> None:
    for value in (14.66, 14.56, 14.66):  # A -> B -> A
        _observe(seeded, _download(seeded), value)

    assert (
        float(seeded.execute(text("SELECT value FROM current_observations")).scalar_one()) == 14.66
    )


def test_one_value_per_key_and_download(seeded: Connection) -> None:
    download = _download(seeded)
    _observe(seeded, download, 14.66)

    message = _rejected(
        seeded,
        INSERT_OBSERVATION,
        {
            "year": 2026,
            "code": 20,
            "start": date(2026, 4, 1),
            "value": 1.0,
            "download_id": download,
        },
    )

    assert "observations_one_per_download" in message


@pytest.mark.parametrize(
    "operation",
    ["UPDATE observations SET value = 0", "DELETE FROM observations", "TRUNCATE observations"],
)
def test_observations_cannot_be_changed_or_removed(seeded: Connection, operation: str) -> None:
    _observe(seeded, _download(seeded), 14.66)

    assert "append-only" in _rejected(seeded, operation)


@pytest.mark.parametrize(
    ("code", "start", "constraint"),
    [
        (23, date(2026, 4, 1), "observations_period_code_known"),
        (20, date(2026, 1, 1), "observations_period_start_matches"),  # Q2 starts in April
        (28, date(2026, 7, 1), "observations_period_start_matches"),  # a year starts in January
    ],
)
def test_the_period_must_be_known_and_coherent(
    seeded: Connection, code: int, start: date, constraint: str
) -> None:
    message = _rejected(
        seeded,
        INSERT_OBSERVATION,
        {
            "year": 2026,
            "code": code,
            "start": start,
            "value": 1.0,
            "download_id": _download(seeded),
        },
    )

    assert constraint in message


def test_a_download_needs_a_known_source_and_a_sha256(seeded: Connection) -> None:
    unknown = _rejected(
        seeded,
        "INSERT INTO downloads (source, url, sha256) VALUES ('wikipedia', 'https://x', :sha)",
        {"sha": SHA},
    )
    not_hex = _rejected(
        seeded,
        "INSERT INTO downloads (source, url, sha256) VALUES ('ine', 'https://x', 'abc')",
    )

    assert "downloads_source_known" in unknown and "downloads_sha256_hex" in not_hex


def test_an_indicator_needs_a_positive_scale_and_a_known_periodicity(seeded: Connection) -> None:
    statement = (
        "INSERT INTO indicators (id, name, unit, scale_factor, periodicity, source_table_id,"
        " description) VALUES ('x', 'X', 'u', :scale, :periodicity, '1', 'd')"
    )

    assert "indicators_scale_positive" in _rejected(
        seeded, statement, {"scale": 0, "periodicity": "annual"}
    )
    assert "indicators_periodicity_known" in _rejected(
        seeded, statement, {"scale": 1, "periodicity": "monthly"}
    )
