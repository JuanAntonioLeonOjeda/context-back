from datetime import date
from operator import attrgetter
from pathlib import Path

import pytest
from sqlalchemy import Connection, text

from datos.governments.application.load_governments import load_competences, load_governments
from datos.governments.application.read_governments import government_on
from datos.governments.domain.government_term import PartyRole
from datos.governments.infrastructure.csv_source import (
    read_competences,
    read_parties,
    read_sectors,
    read_terms,
)
from datos.governments.infrastructure.pg_reader import PgGovernmentsReader
from datos.governments.infrastructure.pg_repository import PgGovernmentRepository
from datos.territories.csv_source import read_territories
from datos.territories.repository import PgTerritoryRepository

pytestmark = pytest.mark.integration

DATA = Path("data/governments")


@pytest.fixture
def reader(db: Connection) -> PgGovernmentsReader:
    PgTerritoryRepository(db).upsert_all(read_territories(Path("data/territories/territories.csv")))
    load_governments(
        PgGovernmentRepository(db),
        read_parties(DATA / "parties.csv"),
        read_terms(DATA / "government_terms.csv", DATA / "government_term_parties.csv"),
        since=date(2020, 1, 1),
        today=date(2026, 10, 13),
    )
    return PgGovernmentsReader(db)


def test_reads_back_every_term_of_the_dataset_with_its_parties(reader: PgGovernmentsReader) -> None:
    expected = read_terms(DATA / "government_terms.csv", DATA / "government_term_parties.csv")

    stored = reader.terms()
    key = attrgetter("territory_id", "valid_from")

    assert len(stored) == len(expected) == 93
    for got, want in zip(sorted(stored, key=key), sorted(expected, key=key), strict=True):
        assert got.valid_to == want.valid_to and got.is_caretaker == want.is_caretaker
        assert sorted(got.parties, key=lambda p: p.party_id) == sorted(
            want.parties, key=lambda p: p.party_id
        )


def test_terms_of_one_territory_only(reader: PgGovernmentsReader) -> None:
    terms = reader.terms("ccaa-09")

    assert terms and {t.territory_id for t in terms} == {"ccaa-09"}


def test_the_government_of_cataluna_today_is_the_psc_with_external_support(
    reader: PgGovernmentsReader,
) -> None:
    term = government_on(reader, "ccaa-09", date(2026, 10, 13))

    assert term is not None
    assert term.governing_party_ids == ("psc",)
    assert {p.party_id for p in term.parties if p.role is PartyRole.EXTERNAL_SUPPORT} == {
        "comuns",
        "erc",
    }


def test_no_government_before_the_dataset_starts(reader: PgGovernmentsReader) -> None:
    assert government_on(reader, "ccaa-13", date(2010, 1, 1)) is None


def test_parties_come_with_their_display_data(reader: PgGovernmentsReader) -> None:
    parties = {p.id: p for p in reader.parties()}

    assert len(parties) == 34
    assert parties["psc"].short_name == "PSC"


def test_competences_are_stored_as_in_the_dataset(
    reader: PgGovernmentsReader, db: Connection
) -> None:
    """The site no longer reads competences (ADR-0018), but they stay curated data: what is
    loaded must be what the CSV says, row by row. `reader` loads the territories and terms the
    competence rules check against."""
    expected = read_competences(DATA / "competences.csv")
    load_competences(PgGovernmentRepository(db), read_sectors(DATA / "sectors.csv"), expected)

    rows = db.execute(
        text(
            "SELECT sector_id, activity, description, level, function, territory_id,"
            " legal_basis, source_url FROM competences"
        )
    ).all()

    assert sorted(tuple(r) for r in rows) == sorted(
        (
            c.sector_id,
            c.activity,
            c.description,
            c.level.value,
            c.function.value,
            c.territory_id,
            c.legal_basis,
            c.source_url,
        )
        for c in expected
    )
    assert len(rows) == 31
