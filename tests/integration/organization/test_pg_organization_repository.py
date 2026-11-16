"""The organisation loaded into PostgreSQL: mirrored from the files, and all or nothing."""

from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import Connection, text

from datos.governments.infrastructure.csv_source import read_sectors
from datos.organization.application.load_organization import (
    InvalidOrganizationError,
    OrganizationCounts,
    load_organization,
)
from datos.organization.domain.body import Body, BodyKind, BodyLevel, Holder
from datos.organization.domain.boxes import Competence
from datos.organization.infrastructure.csv_source import read_organization
from datos.organization.infrastructure.pg_organization_repository import PgOrganizationRepository
from datos.territories.csv_source import read_territories
from datos.territories.repository import PgTerritoryRepository

pytestmark = pytest.mark.integration

SOURCE = "https://example.org/source"


def _body(
    id_: str, kind: BodyKind, level: BodyLevel, territory: str | None, parent: str | None = None
) -> Body:
    return Body(id_, kind, level, territory, f"Name of {id_}", parent, None, SOURCE)


HEAD = _body("ccaa-13-gobierno", BodyKind.EXECUTIVE_HEAD, BodyLevel.CCAA, "ccaa-13")
SANIDAD = _body("ccaa-13-sanidad", BodyKind.DEPARTMENT, BodyLevel.CCAA, "ccaa-13", HEAD.id)
PARLAMENTO = _body("ccaa-13-parlamento", BodyKind.PARLIAMENT, BodyLevel.CCAA, "ccaa-13")
CABILDO = _body("ccaa-05-cabildo", BodyKind.LOCAL, BodyLevel.LOCAL, "ccaa-05")
HOLDER = Holder(SANIDAD.id, "Consejera de Sanidad", "A Person", date(2023, 6, 17), None, SOURCE)
PRESIDENT = Holder(HEAD.id, "Presidenta", "Another Person", date(2023, 6, 17), None, SOURCE)
COMPETENCE = Competence(
    PARLAMENTO.id, "Passes the community's laws", "EA art. 1", ("health", "housing"), SOURCE
)


@pytest.fixture
def repository(db: Connection) -> PgOrganizationRepository:
    PgTerritoryRepository(db).upsert_all(read_territories(Path("data/territories/territories.csv")))
    db.execute(text("INSERT INTO sectors (id, name) VALUES ('health', 'Health'), ('housing', 'H')"))
    return PgOrganizationRepository(db)


def _count(db: Connection, table: str) -> int:
    return int(db.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())  # noqa: S608  # literals of this test


def test_the_files_are_stored_with_the_kind_of_each_holders_body_and_their_sectors(
    repository: PgOrganizationRepository, db: Connection
) -> None:
    # The children come before their parent in the input: the repository orders the inserts.
    counts = load_organization(
        repository, [SANIDAD, PARLAMENTO, CABILDO, HEAD], [HOLDER, PRESIDENT], [COMPETENCE]
    )

    assert counts == OrganizationCounts(bodies=4, holders=2, competences=1)
    kinds = db.execute(text("SELECT body_id, body_kind FROM body_holders ORDER BY 1")).all()
    assert [tuple(row) for row in kinds] == [
        ("ccaa-13-gobierno", "executive_head"),
        ("ccaa-13-sanidad", "department"),
    ]
    sectors = db.execute(text("SELECT sector_id FROM body_competence_sectors ORDER BY 1")).scalars()
    assert list(sectors) == ["health", "housing"]
    parent = db.execute(text("SELECT parent_id FROM bodies WHERE id = :i"), {"i": SANIDAD.id})
    assert parent.scalar_one() == HEAD.id


def test_a_second_load_makes_the_database_mirror_the_new_files(
    repository: PgOrganizationRepository, db: Connection
) -> None:
    load_organization(repository, [HEAD, SANIDAD, PARLAMENTO], [HOLDER], [COMPETENCE])

    load_organization(repository, [HEAD, SANIDAD], [], [])

    assert (_count(db, "bodies"), _count(db, "body_holders")) == (2, 0)
    assert (_count(db, "body_competences"), _count(db, "body_competence_sectors")) == (0, 0)


def test_a_dataset_with_a_problem_leaves_what_was_stored_untouched(
    repository: PgOrganizationRepository, db: Connection
) -> None:
    load_organization(repository, [HEAD, SANIDAD, PARLAMENTO], [HOLDER], [COMPETENCE])
    orphan = Holder("ccaa-13-nada", "Post", "Nobody", date(2023, 1, 1), None, SOURCE)

    with pytest.raises(InvalidOrganizationError):
        load_organization(repository, [HEAD], [orphan], [])

    assert (_count(db, "bodies"), _count(db, "body_holders")) == (3, 1)
    assert _count(db, "body_competences") == 1


def test_the_real_files_load_into_an_empty_organisation(
    repository: PgOrganizationRepository, db: Connection
) -> None:
    # The competences of the real files may relate to any sector of the real taxonomy.
    for sector in read_sectors(Path("data/governments/sectors.csv")):
        db.execute(
            text("INSERT INTO sectors (id, name) VALUES (:id, :name) ON CONFLICT DO NOTHING"),
            {"id": sector.id, "name": sector.name},
        )
    bodies, holders, competences = read_organization(Path("data/organization"))

    counts = load_organization(repository, bodies, holders, competences)

    assert counts.bodies == _count(db, "bodies")
