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
from datos.voters.domain.dimensions import DimensionId
from datos.voters.infrastructure.infoelectoral import read_election_zip
from datos.voters.infrastructure.pg_election_repository import PgElectionRepository
from datos.voters.infrastructure.pg_voters_reader import CENSO_ANUAL_URL, PgVotersReader

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
    rows = reader.municipal_rows("ccaa-05", "congreso-2023-07", 2023, DimensionId.EDUCATION)

    by_code = {r.code: r for r in rows}
    assert set(by_code) == {"35016", "38038"}
    assert by_code["35016"].income == Decimal("14968.00")
    assert by_code["38038"].income is None  # no income loaded for it


def test_counts_come_by_candidature_and_match_the_municipal_total(
    reader: PgVotersReader, db: Connection
) -> None:
    rows = reader.municipal_rows("ccaa-05", "congreso-2023-07", 2023, DimensionId.EDUCATION)

    for row in rows:
        stored = db.execute(
            text("SELECT candidature_votes FROM municipal_results WHERE municipality_code = :c"),
            {"c": row.code},
        ).scalar_one()
        assert sum(c.votes for c in row.counts) == stored
    # Sumar's list in the Canaries (000033) comes as itself, not as its national head (000010):
    # whether it counts as Sumar is the curated table's to say.
    candidatures = {(c.code, c.acronym) for r in rows for c in r.counts}
    assert ("000033", "SUMAR") in candidatures
    assert all(code != "000010" for code, _ in candidatures)


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

    by_code = {
        r.code: r
        for r in reader.municipal_rows("ccaa-05", "congreso-2023-07", 2023, DimensionId.EDUCATION)
    }

    assert set(by_code) == {"35001", "35016", "38038"}
    empty = by_code["35001"]
    assert (empty.census, empty.blank_votes, empty.income, empty.counts) == (10, 2, None, ())
    assert by_code["35016"].counts  # the others keep their counts


def test_another_community_has_no_rows(reader: PgVotersReader) -> None:
    assert reader.municipal_rows("ccaa-13", "congreso-2023-07", 2023, DimensionId.EDUCATION) == []


def test_names_the_latest_income_download_of_the_year(reader: PgVotersReader) -> None:
    download = reader.income_download(2023)

    assert download is not None
    assert download.url == NEW_URL
    assert reader.income_download(2019) is None


def _education_load(
    db: Connection,
    sha: str,
    year: int,
    values: dict[str, str],
    loaded_at: str = "2026-11-16",
    dimension: str = "education",
) -> None:
    load_id = db.execute(
        text(
            "INSERT INTO municipal_value_loads"
            " (dimension, source_url, source_file, source_sha256, loaded_at)"
            " VALUES (:dimension, 'https://www.ine.es/t', '66620.csv', :sha, :loaded_at)"
            " RETURNING id"
        ),
        {"sha": sha * 64, "loaded_at": loaded_at, "dimension": dimension},
    ).scalar_one()
    for code, value in values.items():
        db.execute(
            text(
                "INSERT INTO municipal_values (load_id, municipality_code, year, value)"
                " VALUES (:load, :code, :year, :value)"
            ),
            {"load": load_id, "code": code, "year": year, "value": Decimal(value)},
        )


def test_gives_each_municipality_its_latest_education_of_the_year(
    reader: PgVotersReader, db: Connection
) -> None:
    _education_load(db, "a", 2023, {"35016": "33.000", "38038": "36.000"})
    _education_load(db, "b", 2023, {"35016": "33.052"})  # a revision: the newer load wins
    _education_load(db, "c", 2022, {"38038": "10.000"})  # another year: not this election's

    by_code = {
        r.code: r
        for r in reader.municipal_rows("ccaa-05", "congreso-2023-07", 2023, DimensionId.EDUCATION)
    }

    assert by_code["35016"].loaded_value == Decimal("33.052")
    assert by_code["38038"].loaded_value == Decimal("36.000")


def test_a_municipality_without_education_has_none(reader: PgVotersReader) -> None:
    rows = reader.municipal_rows("ccaa-05", "congreso-2023-07", 2023, DimensionId.EDUCATION)

    assert all(r.loaded_value is None for r in rows)


def test_names_the_census_page_and_the_latest_education_load_of_the_year(
    reader: PgVotersReader, db: Connection
) -> None:
    _education_load(db, "a", 2023, {"35016": "33.000"})
    _education_load(db, "b", 2022, {"35016": "32.000"})

    source = reader.values_source(DimensionId.EDUCATION, 2023)

    assert source is not None
    assert source.url == CENSO_ANUAL_URL
    assert source.year == 2023
    assert reader.values_source(DimensionId.EDUCATION, 2019) is None


def test_the_education_source_is_loaded_when_its_latest_load_of_the_year_was(
    reader: PgVotersReader, db: Connection
) -> None:
    _education_load(db, "a", 2023, {"35016": "33.000"}, loaded_at="2026-11-16")
    _education_load(db, "b", 2023, {"38038": "36.000"}, loaded_at="2026-12-01")

    source = reader.values_source(DimensionId.EDUCATION, 2023)

    assert source is not None
    assert str(source.fetched_at.date()) == "2026-12-01"


def test_each_dimension_gets_only_its_own_values_and_its_own_load(
    reader: PgVotersReader, db: Connection
) -> None:
    _education_load(db, "a", 2023, {"35016": "33.000"}, "2026-11-16", "education")
    _education_load(db, "b", 2023, {"35016": "11.215"}, "2026-12-01", "age")

    def value(dimension: DimensionId) -> object:
        rows = reader.municipal_rows("ccaa-05", "congreso-2023-07", 2023, dimension)
        return {r.code: r.loaded_value for r in rows}["35016"]

    assert value(DimensionId.EDUCATION) == Decimal("33.000")
    assert value(DimensionId.AGE) == Decimal("11.215")
    assert value(DimensionId.BORN_ABROAD) is None
    assert value(DimensionId.INCOME) is None  # not a loaded dimension: no load has its name
    education = reader.values_source(DimensionId.EDUCATION, 2023)
    age = reader.values_source(DimensionId.AGE, 2023)
    assert education is not None and age is not None
    assert education.fetched_at < age.fetched_at  # each one has the date of its own load
    assert reader.values_source(DimensionId.BORN_ABROAD, 2023) is None
