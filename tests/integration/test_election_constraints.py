"""The rules migration 0015 promises for election results and income, checked on PostgreSQL."""

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError

pytestmark = pytest.mark.integration

SHA = "0" * 64
ELECTION = "congreso-2023-07"


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
    db.execute(
        text(
            "INSERT INTO elections (id, kind, held_on, source_file, source_sha256)"
            " VALUES (:id, 'congreso', '2023-07-23', '02202307_MUNI.zip', :sha)"
        ),
        {"id": ELECTION, "sha": SHA},
    )
    _candidature(db, "000002", head="000002")
    _result(db, "35016")
    return db


def _candidature(db: Connection, code: str, *, head: str) -> None:
    db.execute(
        text(
            "INSERT INTO election_candidatures"
            " (election_id, code, acronym, name, national_head_code)"
            " VALUES (:e, :code, 'X', 'Candidature X', :head)"
        ),
        {"e": ELECTION, "code": code, "head": head},
    )


def _result(db: Connection, code: str, *, census: int = 100) -> None:
    db.execute(
        text(
            "INSERT INTO municipal_results (election_id, municipality_code, municipality_name,"
            " census, blank_votes, null_votes, candidature_votes)"
            " VALUES (:e, :code, 'Municipio', :census, 1, 1, 60)"
        ),
        {"e": ELECTION, "code": code, "census": census},
    )


def _votes(db: Connection, municipality: str, candidature: str, votes: int = 60) -> None:
    db.execute(
        text(
            "INSERT INTO municipal_candidature_votes"
            " (election_id, municipality_code, candidature_code, votes)"
            " VALUES (:e, :m, :c, :v)"
        ),
        {"e": ELECTION, "m": municipality, "c": candidature, "v": votes},
    )


def _fails(db: Connection, statement: str, constraint: str, **params: object) -> None:
    with pytest.raises(DBAPIError) as error, db.begin_nested():
        db.execute(text(statement), params)
        db.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert constraint in str(error.value)


def test_a_complete_municipality_is_stored_with_its_province(seeded: Connection) -> None:
    _votes(seeded, "35016", "000002")

    province = seeded.execute(
        text("SELECT province_id FROM municipal_results WHERE municipality_code = '35016'")
    ).scalar_one()
    assert province == "prov-35"


def test_a_municipality_of_an_unknown_province_is_refused(seeded: Connection) -> None:
    _fails(
        seeded,
        "INSERT INTO municipal_results (election_id, municipality_code, municipality_name,"
        " census, blank_votes, null_votes, candidature_votes) VALUES (:e, '99001',"
        " 'Nowhere', 1, 0, 0, 1)",
        "municipal_results_province_id_fkey",
        e=ELECTION,
    )


def test_a_municipality_code_must_have_five_digits(seeded: Connection) -> None:
    _fails(
        seeded,
        "INSERT INTO municipal_results (election_id, municipality_code, municipality_name,"
        " census, blank_votes, null_votes, candidature_votes) VALUES (:e, '3501',"
        " 'Short', 1, 0, 0, 1)",
        "municipal_results_code_5_digits",
        e=ELECTION,
    )


def test_negative_counts_are_refused(seeded: Connection) -> None:
    _fails(
        seeded,
        "INSERT INTO municipal_results (election_id, municipality_code, municipality_name,"
        " census, blank_votes, null_votes, candidature_votes) VALUES (:e, '35001',"
        " 'Negative', 10, -1, 0, 5)",
        "municipal_results_counts_not_negative",
        e=ELECTION,
    )


def test_votes_of_a_candidature_the_election_does_not_have_are_refused(
    seeded: Connection,
) -> None:
    _fails(
        seeded,
        "INSERT INTO municipal_candidature_votes (election_id, municipality_code,"
        " candidature_code, votes) VALUES (:e, '35016', '000099', 3)",
        "municipal_candidature_votes_candidature",
        e=ELECTION,
    )


def test_votes_of_a_municipality_without_results_are_refused(seeded: Connection) -> None:
    _fails(
        seeded,
        "INSERT INTO municipal_candidature_votes (election_id, municipality_code,"
        " candidature_code, votes) VALUES (:e, '35001', '000002', 3)",
        "municipal_candidature_votes_result",
        e=ELECTION,
    )


def test_a_candidature_may_come_before_its_national_head_in_the_same_transaction(
    seeded: Connection,
) -> None:
    with seeded.begin_nested():
        _candidature(seeded, "000047", head="000010")  # PSC-like: its head comes after it
        _candidature(seeded, "000010", head="000010")
        seeded.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


def test_a_national_head_that_never_arrives_is_refused(seeded: Connection) -> None:
    _fails(
        seeded,
        "INSERT INTO election_candidatures (election_id, code, acronym, name, national_head_code)"
        " VALUES (:e, '000047', 'PSC', 'PSC', '000010')",
        "election_candidatures_head_exists",
        e=ELECTION,
    )


def test_the_same_file_cannot_be_two_elections(seeded: Connection) -> None:
    _fails(
        seeded,
        "INSERT INTO elections (id, kind, held_on, source_file, source_sha256)"
        " VALUES ('congreso-2026-11', 'congreso', '2026-11-29', 'copy.zip', :sha)",
        "elections_one_file",
        sha=SHA,
    )


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE municipal_results SET census = 1",
        "DELETE FROM municipal_results",
        "TRUNCATE municipal_candidature_votes, municipal_results CASCADE",
    ],
)
def test_results_are_append_only(seeded: Connection, statement: str) -> None:
    _fails(seeded, statement, "append-only")


def test_income_is_append_only_and_keeps_its_download(seeded: Connection) -> None:
    download = seeded.execute(
        text(
            "INSERT INTO downloads (source, url, sha256) VALUES"
            " ('ine', 'https://servicios.ine.es/wstempus/js/ES/DATOS_METADATAOPERACION/353', :sha)"
            " RETURNING id"
        ),
        {"sha": SHA},
    ).scalar_one()
    seeded.execute(
        text(
            "INSERT INTO municipal_income (municipality_code, year, euros_per_person,"
            " series_code, download_id)"
            " VALUES ('35016', 2023, 12345.67, 'ADRH1', :d)"
        ),
        {"d": download},
    )

    _fails(seeded, "UPDATE municipal_income SET euros_per_person = 1", "append-only")
    _fails(
        seeded,
        "INSERT INTO municipal_income (municipality_code, year, euros_per_person,"
        " series_code, download_id) VALUES ('35016', 2023, 0, 'ADRH1', :d)",
        "municipal_income_positive",
        d=download,
    )
