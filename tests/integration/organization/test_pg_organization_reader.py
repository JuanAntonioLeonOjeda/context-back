"""The organisation read back from PostgreSQL as the domain types, in the order of the files."""

from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import Connection, text

from datos.organization.application.load_organization import load_organization
from datos.organization.domain.body import Body, BodyKind, BodyLevel, Holder
from datos.organization.domain.boxes import Competence
from datos.organization.infrastructure.pg_organization_reader import PgOrganizationReader
from datos.organization.infrastructure.pg_organization_repository import PgOrganizationRepository
from datos.territories.csv_source import read_territories
from datos.territories.repository import PgTerritoryRepository

pytestmark = pytest.mark.integration

SOURCE = "https://example.org/source"
HEAD = Body(
    "ccaa-13-gobierno", BodyKind.EXECUTIVE_HEAD, BodyLevel.CCAA, "ccaa-13", "Presidencia", None,
    "A13000001", SOURCE,
)  # fmt: skip
SANIDAD = Body(
    "ccaa-13-sanidad",
    BodyKind.DEPARTMENT,
    BodyLevel.CCAA,
    "ccaa-13",
    "Sanidad",
    HEAD.id,
    None,
    SOURCE,
)
TSJ = Body("ccaa-13-tsj", BodyKind.JUDICIARY, BodyLevel.STATE, "ccaa-13", "TSJ", None, None, SOURCE)
LOCAL = Body(
    "local-ayuntamiento", BodyKind.LOCAL, BodyLevel.LOCAL, None, "Ayuntamiento", None, None, SOURCE
)
HOLDER = Holder(SANIDAD.id, "Consejera de Sanidad", "A Person", date(2023, 6, 17), None, SOURCE)
SECOND = Competence(SANIDAD.id, "Second in the file", "Art. 2", ("health",), SOURCE)
FIRST = Competence(SANIDAD.id, "First in the file", "Art. 1", ("housing", "health"), SOURCE)


@pytest.fixture
def reader(db: Connection) -> PgOrganizationReader:
    PgTerritoryRepository(db).upsert_all(read_territories(Path("data/territories/territories.csv")))
    db.execute(
        text("INSERT INTO sectors (id, name) VALUES ('health', 'Sanidad'), ('housing', 'Vivienda')")
    )
    return PgOrganizationReader(db)


def _load(
    db: Connection, bodies: list[Body], holders: list[Holder], competences: list[Competence]
) -> None:
    load_organization(PgOrganizationRepository(db), bodies, holders, competences)


def test_what_was_loaded_is_read_back_as_the_domain_types(
    reader: PgOrganizationReader, db: Connection
) -> None:
    _load(db, [LOCAL, TSJ, SANIDAD, HEAD], [HOLDER], [FIRST])

    assert sorted(reader.bodies(), key=lambda b: b.id) == sorted(
        [HEAD, SANIDAD, TSJ, LOCAL], key=lambda b: b.id
    )
    assert reader.holders() == [HOLDER]


def test_the_period_of_a_body_is_read_back(reader: PgOrganizationReader, db: Connection) -> None:
    closed = replace(SANIDAD, valid_from=date(2019, 8, 20), valid_to=date(2026, 1, 1))

    _load(db, [HEAD, closed], [], [])

    assert {b.id: (b.valid_from, b.valid_to) for b in reader.bodies()} == {
        HEAD.id: (None, None),
        closed.id: (date(2019, 8, 20), date(2026, 1, 1)),
    }


def test_the_competences_keep_the_order_of_the_file_and_their_sectors_come_sorted(
    reader: PgOrganizationReader, db: Connection
) -> None:
    _load(db, [HEAD, SANIDAD], [], [SECOND, FIRST])

    competences = reader.competences()

    assert [c.summary for c in competences] == ["Second in the file", "First in the file"]
    assert competences[1].sector_ids == ("health", "housing")  # sorted, not in the file's order
    assert competences[0].legal_basis == "Art. 2"


def test_the_sector_names_are_those_of_the_whole_taxonomy(
    reader: PgOrganizationReader,
) -> None:
    assert reader.sector_names() == {"health": "Sanidad", "housing": "Vivienda"}


def test_an_empty_organisation_reads_as_nothing(reader: PgOrganizationReader) -> None:
    assert (reader.bodies(), reader.holders(), reader.competences()) == ([], [], [])


def test_holders_of_a_body_come_in_the_order_of_their_periods(
    reader: PgOrganizationReader, db: Connection
) -> None:
    older = Holder(SANIDAD.id, "Consejero", "Older", date(2020, 1, 1), date(2023, 6, 17), SOURCE)

    _load(db, [HEAD, SANIDAD], [HOLDER, older], [])

    assert [(h.holder_name, h.valid_to) for h in reader.holders()] == [
        ("Older", date(2023, 6, 17)),
        ("A Person", None),
    ]


def test_a_competence_with_no_sector_still_comes_with_none(
    reader: PgOrganizationReader, db: Connection
) -> None:
    # The loader refuses it, but the table allows it: the reader must not drop it.
    _load(db, [HEAD, SANIDAD], [], [])
    db.execute(
        text(
            "INSERT INTO body_competences (body_id, summary, legal_basis, source_url)"
            " VALUES ('ccaa-13-sanidad', 'No sector', 'Art. 3', 'https://example.org/s')"
        )
    )

    [competence] = reader.competences()

    assert (competence.summary, competence.sector_ids) == ("No sector", ())
