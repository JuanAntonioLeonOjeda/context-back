"""The voters reader on the real fixture zip (Las Palmas de Gran Canaria and Santa Cruz de
Tenerife, 2023 Congreso) and two income downloads."""

import zipfile
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import Connection, text

from datos.territories.csv_source import read_territories
from datos.territories.repository import PgTerritoryRepository
from datos.voters.application.load_election import load_election
from datos.voters.infrastructure.infoelectoral import read_election_zip
from datos.voters.infrastructure.pg_election_repository import PgElectionRepository
from datos.voters.infrastructure.pg_voters_reader import PgVotersReader

pytestmark = pytest.mark.integration

FIXTURE = Path("tests/fixtures/infoelectoral/02202307_MUNI")
OLD_URL = "https://servicios.ine.es/wstempus/js/ES/DATOS_METADATAOPERACION/353?old"
NEW_URL = "https://servicios.ine.es/wstempus/js/ES/DATOS_METADATAOPERACION/353?new"


def _download(db: Connection, url: str) -> int:
    return int(
        db.execute(
            text("INSERT INTO downloads (source, url, sha256) VALUES ('ine', :u, :s) RETURNING id"),
            {"u": url, "s": "e" * 64},
        ).scalar_one()
    )


def _income(db: Connection, code: str, euros: str, download_id: int) -> None:
    db.execute(
        text(
            "INSERT INTO municipal_income (municipality_code, year, euros_per_person, series_code,"
            " download_id) VALUES (:c, 2023, :e, 'ADRH', :d)"
        ),
        {"c": code, "e": Decimal(euros), "d": download_id},
    )


@pytest.fixture
def reader(db: Connection, tmp_path: Path) -> PgVotersReader:
    PgTerritoryRepository(db).upsert_all(read_territories(Path("data/territories/territories.csv")))
    path = tmp_path / "02202307_MUNI.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for file in sorted(FIXTURE.iterdir()):
            archive.write(file, file.name)
    load_election(PgElectionRepository(db), read_election_zip(path))
    old = _download(db, OLD_URL)
    _income(db, "35016", "14000", old)
    new = _download(db, NEW_URL)
    _income(db, "35016", "14968", new)  # a revision: the newer download wins
    return PgVotersReader(db)


def test_lists_the_loaded_election(reader: PgVotersReader) -> None:
    [election] = reader.elections()

    assert (election.id, str(election.held_on), election.source_file) == (
        "congreso-2023-07",
        "2023-07-23",
        "02202307_MUNI.zip",
    )


def test_gives_each_municipality_of_the_community_with_its_latest_income(
    reader: PgVotersReader,
) -> None:
    rows = reader.municipal_rows("ccaa-05", "congreso-2023-07", 2023)

    by_code = {r.code: r for r in rows}
    assert set(by_code) == {"35016", "38038"}
    assert by_code["35016"].income == Decimal("14968.00")
    assert by_code["38038"].income is None  # no income loaded for it


def test_counts_add_up_by_national_head_and_match_the_municipal_total(
    reader: PgVotersReader, db: Connection
) -> None:
    rows = reader.municipal_rows("ccaa-05", "congreso-2023-07", 2023)

    for row in rows:
        stored = db.execute(
            text("SELECT candidature_votes FROM municipal_results WHERE municipality_code = :c"),
            {"c": row.code},
        ).scalar_one()
        assert sum(c.votes for c in row.counts) == stored
    # Sumar's list in the Canaries (000033) adds up to Sumar's head (000010).
    heads = {(c.head_code, c.head_acronym) for r in rows for c in r.counts}
    assert ("000010", "SUMAR") in heads
    assert all(code != "000033" for code, _ in heads)


def test_a_municipality_where_no_candidature_got_a_vote_still_comes(
    reader: PgVotersReader, db: Connection
) -> None:
    db.execute(
        text(
            "INSERT INTO municipal_results (election_id, municipality_code, municipality_name,"
            " census, blank_votes, null_votes, candidature_votes)"
            " VALUES ('congreso-2023-07', '35001', 'Only blank votes', 10, 2, 0, 0)"
        )
    )

    by_code = {r.code: r for r in reader.municipal_rows("ccaa-05", "congreso-2023-07", 2023)}

    assert set(by_code) == {"35001", "35016", "38038"}
    empty = by_code["35001"]
    assert (empty.census, empty.blank_votes, empty.income, empty.counts) == (10, 2, None, ())
    assert by_code["35016"].counts  # the others keep their counts


def test_another_community_has_no_rows(reader: PgVotersReader) -> None:
    assert reader.municipal_rows("ccaa-13", "congreso-2023-07", 2023) == []


def test_names_the_latest_income_download_of_the_year(reader: PgVotersReader) -> None:
    download = reader.income_download(2023)

    assert download is not None
    assert download.url == NEW_URL
    assert reader.income_download(2019) is None
