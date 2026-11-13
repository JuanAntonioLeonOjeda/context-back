"""Loading the real fixture zip (two municipalities of the 2023 Congreso) into PostgreSQL."""

import zipfile
from pathlib import Path

import pytest
from sqlalchemy import Connection, text

from datos.territories.csv_source import read_territories
from datos.territories.repository import PgTerritoryRepository
from datos.voters.application.load_election import LoadOutcome, load_election
from datos.voters.infrastructure.infoelectoral import read_election_zip
from datos.voters.infrastructure.pg_election_repository import PgElectionRepository

pytestmark = pytest.mark.integration

FIXTURE = Path("tests/fixtures/infoelectoral/02202307_MUNI")


@pytest.fixture
def repository(db: Connection) -> PgElectionRepository:
    PgTerritoryRepository(db).upsert_all(read_territories(Path("data/territories/territories.csv")))
    return PgElectionRepository(db)


@pytest.fixture
def zip_path(tmp_path: Path) -> Path:
    path = tmp_path / "02202307_MUNI.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for file in sorted(FIXTURE.iterdir()):
            archive.write(file, file.name)
    return path


def _count(db: Connection, table: str) -> int:
    return int(db.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())  # noqa: S608  # table names are literals of this test


def test_stores_the_election_once_and_a_second_load_writes_nothing(
    repository: PgElectionRepository, db: Connection, zip_path: Path
) -> None:
    file = read_election_zip(zip_path)

    assert load_election(repository, file) is LoadOutcome.LOADED
    assert load_election(repository, file) is LoadOutcome.ALREADY_LOADED

    assert _count(db, "elections") == 1
    assert _count(db, "election_candidatures") == 12
    assert _count(db, "municipal_results") == 2
    assert _count(db, "municipal_candidature_votes") == 20
    assert repository.stored_sha256("congreso-2023-07") == file.sha256


def test_each_municipality_reaches_its_community_through_its_province(
    repository: PgElectionRepository, db: Connection, zip_path: Path
) -> None:
    load_election(repository, read_election_zip(zip_path))

    communities = db.execute(
        text(
            "SELECT r.municipality_code, t.parent_id FROM municipal_results r"
            " JOIN territories t ON t.id = r.province_id ORDER BY 1"
        )
    ).all()
    assert [tuple(row) for row in communities] == [("35016", "ccaa-05"), ("38038", "ccaa-05")]


def test_the_stored_votes_add_up_to_each_municipal_total(
    repository: PgElectionRepository, db: Connection, zip_path: Path
) -> None:
    load_election(repository, read_election_zip(zip_path))

    mismatches = db.execute(
        text(
            "SELECT r.municipality_code FROM municipal_results r"
            " JOIN municipal_candidature_votes v USING (election_id, municipality_code)"
            " GROUP BY r.municipality_code, r.candidature_votes"
            " HAVING sum(v.votes) <> r.candidature_votes"
        )
    ).all()
    assert mismatches == []
