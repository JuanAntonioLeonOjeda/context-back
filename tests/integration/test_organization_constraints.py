"""The rules migration 0016 promises for bodies, holders and competences, checked on PostgreSQL."""

from datetime import date

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError

pytestmark = pytest.mark.integration

SOURCE = "https://example.org/source"


@pytest.fixture
def seeded(db: Connection) -> Connection:
    db.execute(
        text(
            "INSERT INTO territories (id, ine_code, name, level, parent_id) VALUES"
            " ('es', NULL, 'España', 'state', NULL),"
            " ('ccaa-13', '13', 'Community A', 'ccaa', 'es'),"
            " ('ccaa-14', '14', 'Community B', 'ccaa', 'es'),"
            " ('prov-28', '28', 'Province A', 'province', 'ccaa-13')"
        )
    )
    db.execute(text("INSERT INTO sectors (id, name) VALUES ('health', 'Health')"))
    _body(db, "ccaa-13-gobierno", kind="executive_head", level="ccaa", territory="ccaa-13")
    return db


def _body(
    db: Connection,
    body_id: str,
    *,
    kind: str,
    level: str,
    territory: str | None,
    parent: str | None = None,
    dir3: str | None = None,
) -> None:
    db.execute(
        text(
            "INSERT INTO bodies (id, kind, level, territory_id, name, parent_id, dir3_id,"
            " source_url) VALUES (:id, :kind, :level, :territory, 'A body', :parent, :dir3,"
            " :source)"
        ),
        {
            "id": body_id,
            "kind": kind,
            "level": level,
            "territory": territory,
            "parent": parent,
            "dir3": dir3,
            "source": SOURCE,
        },
    )


def _holder(
    db: Connection, body_id: str, valid_from: date, valid_to: date | None, kind: str = "department"
) -> None:
    db.execute(
        text(
            "INSERT INTO body_holders (body_id, body_kind, post_title, holder_name, valid_from,"
            " valid_to, source_url) VALUES (:body, :kind, 'Consejero', 'A Person', :f, :t, :source)"
        ),
        {"body": body_id, "kind": kind, "f": valid_from, "t": valid_to, "source": SOURCE},
    )


def _fails(db: Connection, statement: str, constraint: str, **params: object) -> None:
    with pytest.raises(DBAPIError) as error, db.begin_nested():
        db.execute(text(statement), params)
    assert constraint in str(error.value)


def _body_fails(
    db: Connection,
    constraint: str,
    body_id: str,
    kind: str,
    level: str,
    territory: str | None,
    parent: str | None = None,
) -> None:
    """Insert a body that must break exactly this rule (PostgreSQL names the first broken one)."""
    _fails(
        db,
        "INSERT INTO bodies (id, kind, level, territory_id, name, parent_id, source_url)"
        " VALUES (:id, :kind, :level, :territory, 'A body', :parent, 'https://example.org/source')",
        constraint,
        id=body_id,
        kind=kind,
        level=level,
        territory=territory,
        parent=parent,
    )


# --- bodies --------------------------------------------------------------------------


def test_a_department_of_a_community_is_stored_under_its_executive(seeded: Connection) -> None:
    _body(
        seeded,
        "ccaa-13-sanidad",
        kind="department",
        level="ccaa",
        territory="ccaa-13",
        parent="ccaa-13-gobierno",
        dir3="A13002915",
    )

    parent = seeded.execute(
        text("SELECT parent_id FROM bodies WHERE id = 'ccaa-13-sanidad'")
    ).scalar_one()
    assert parent == "ccaa-13-gobierno"


def test_a_local_body_is_generic_or_belongs_to_a_community(seeded: Connection) -> None:
    _body(seeded, "local-ayuntamiento", kind="local", level="local", territory=None)
    _body(seeded, "ccaa-13-cabildo", kind="local", level="local", territory="ccaa-13")

    # Its id starts with the territory, so this is the only rule each one breaks.
    for territory in ("es", "prov-28"):
        _body_fails(
            seeded,
            "bodies_local_is_generic_or_of_a_community",
            f"{territory}-cabildo",
            "local",
            "local",
            territory,
        )


def test_only_a_local_body_may_have_no_territory(seeded: Connection) -> None:
    # A State court with no territory: the check on the State's bodies would also refuse it, but
    # PostgreSQL names the first broken rule in alphabetical order, and this one comes first.
    _body_fails(
        seeded, "bodies_only_local_has_no_territory", "local-tribunal", "judiciary", "state", None
    )


@pytest.mark.parametrize("territory", ["es", "prov-28", None])
def test_a_body_of_a_community_belongs_to_a_community(
    seeded: Connection, territory: str | None
) -> None:
    id_ = f"{territory}-parlamento" if territory else "local-parlamento"
    _body_fails(seeded, "bodies_ccaa_belongs_to_a_community", id_, "parliament", "ccaa", territory)


def test_a_state_body_belongs_to_the_state_except_a_court(seeded: Connection) -> None:
    _body(seeded, "ccaa-13-tsj", kind="judiciary", level="state", territory="ccaa-13")

    _body_fails(
        seeded,
        "bodies_state_belongs_to_the_state",
        "ccaa-13-ministerio",
        "department",
        "state",
        "ccaa-13",
        parent="ccaa-13-gobierno",
    )
    _body_fails(
        seeded,
        "bodies_state_belongs_to_the_state",
        "prov-28-audiencia",
        "judiciary",
        "state",
        "prov-28",
    )


def test_the_id_starts_with_its_territory(seeded: Connection) -> None:
    _body_fails(
        seeded,
        "bodies_id_starts_with_its_territory",
        "ccaa-14-parlamento",
        "parliament",
        "ccaa",
        "ccaa-13",
    )
    _body_fails(seeded, "bodies_id_starts_with_its_territory", "cabildo", "local", "local", None)


def test_a_department_needs_a_parent_and_a_body_is_not_its_own_parent(seeded: Connection) -> None:
    _body_fails(
        seeded, "bodies_department_has_a_parent", "ccaa-13-sanidad", "department", "ccaa", "ccaa-13"
    )
    _body_fails(
        seeded,
        "bodies_parent_is_another_body",
        "ccaa-13-uno",
        "parliament",
        "ccaa",
        "ccaa-13",
        parent="ccaa-13-uno",
    )


def test_the_dir3_code_has_its_format_and_belongs_to_one_body(seeded: Connection) -> None:
    _body(
        seeded,
        "ccaa-13-parlamento",
        kind="parliament",
        level="ccaa",
        territory="ccaa-13",
        dir3="A13002915",
    )

    with pytest.raises(DBAPIError) as error, seeded.begin_nested():
        _body(
            seeded,
            "ccaa-13-otro",
            kind="parliament",
            level="ccaa",
            territory="ccaa-13",
            dir3="A13002915",
        )
    assert "bodies_dir3_id_unique" in str(error.value)
    with pytest.raises(DBAPIError) as error, seeded.begin_nested():
        _body(
            seeded, "ccaa-13-malo", kind="parliament", level="ccaa", territory="ccaa-13", dir3="a13"
        )
    assert "bodies_dir3_id_format" in str(error.value)


def test_a_body_needs_a_source_that_is_a_url_and_a_name(seeded: Connection) -> None:
    _fails(
        seeded,
        "INSERT INTO bodies (id, kind, level, territory_id, name, source_url)"
        " VALUES ('ccaa-13-uno', 'parliament', 'ccaa', 'ccaa-13', 'A body', 'not a url')",
        "bodies_source_is_url",
    )
    _fails(
        seeded,
        "INSERT INTO bodies (id, kind, level, territory_id, name, source_url)"
        " VALUES ('ccaa-13-dos', 'parliament', 'ccaa', 'ccaa-13', '  ', 'https://example.org/s')",
        "bodies_name_not_empty",
    )


# --- holders -------------------------------------------------------------------------


def _department(db: Connection, body_id: str = "ccaa-13-sanidad") -> None:
    _body(
        db, body_id, kind="department", level="ccaa", territory="ccaa-13", parent="ccaa-13-gobierno"
    )


def test_the_day_of_the_change_belongs_to_the_new_holder(seeded: Connection) -> None:
    _department(seeded)
    _holder(seeded, "ccaa-13-sanidad", date(2023, 6, 17), date(2026, 3, 1))
    _holder(seeded, "ccaa-13-sanidad", date(2026, 3, 1), None)


def test_two_holders_of_one_body_never_overlap_and_an_open_period_collides_with_a_later_one(
    seeded: Connection,
) -> None:
    _department(seeded)
    _holder(seeded, "ccaa-13-sanidad", date(2023, 6, 17), date(2026, 3, 1))

    _fails(
        seeded,
        "INSERT INTO body_holders (body_id, body_kind, post_title, holder_name, valid_from,"
        " valid_to, source_url) VALUES ('ccaa-13-sanidad', 'department', 'C', 'B', '2026-2-28',"
        " NULL, 'https://example.org/s')",
        "body_holders_no_overlap",
    )
    _holder(seeded, "ccaa-13-sanidad", date(2026, 3, 1), None)
    _fails(
        seeded,
        "INSERT INTO body_holders (body_id, body_kind, post_title, holder_name, valid_from,"
        " valid_to, source_url) VALUES ('ccaa-13-sanidad', 'department', 'C', 'B', '2030-1-1',"
        " NULL, 'https://example.org/s')",
        "body_holders_no_overlap",
    )


def test_two_bodies_may_have_a_holder_on_the_same_days(seeded: Connection) -> None:
    _department(seeded, "ccaa-13-sanidad")
    _department(seeded, "ccaa-13-educacion")
    _holder(seeded, "ccaa-13-sanidad", date(2023, 6, 17), None)
    _holder(seeded, "ccaa-13-educacion", date(2023, 6, 17), None)


def test_only_the_head_of_an_executive_and_a_department_have_a_holder(seeded: Connection) -> None:
    _body(seeded, "ccaa-13-parlamento", kind="parliament", level="ccaa", territory="ccaa-13")
    _holder(seeded, "ccaa-13-gobierno", date(2023, 6, 17), None, kind="executive_head")

    # The kind it states is not its body's kind: the foreign key refuses it.
    _fails(
        seeded,
        "INSERT INTO body_holders (body_id, body_kind, post_title, holder_name, valid_from,"
        " source_url) VALUES ('ccaa-13-parlamento', 'department', 'C', 'B', '2023-6-17',"
        " 'https://example.org/s')",
        "body_holders_body_fkey",
    )
    # The kind it states is its body's, but that kind has no holder: the check refuses it.
    _fails(
        seeded,
        "INSERT INTO body_holders (body_id, body_kind, post_title, holder_name, valid_from,"
        " source_url) VALUES ('ccaa-13-parlamento', 'parliament', 'C', 'B', '2023-6-17',"
        " 'https://example.org/s')",
        "body_holders_kind_has_a_holder",
    )


def test_a_holder_period_is_not_empty_and_has_a_source_that_is_a_url(seeded: Connection) -> None:
    _fails(
        seeded,
        "INSERT INTO body_holders (body_id, body_kind, post_title, holder_name, valid_from,"
        " valid_to, source_url) VALUES ('ccaa-13-gobierno', 'executive_head', 'P', 'N',"
        " '2023-6-17', '2023-6-17', 'https://example.org/s')",
        "body_holders_period_not_empty",
    )
    _fails(
        seeded,
        "INSERT INTO body_holders (body_id, body_kind, post_title, holder_name, valid_from,"
        " source_url) VALUES ('ccaa-13-gobierno', 'executive_head', 'P', 'N', '2023-6-17', 'x')",
        "body_holders_source_is_url",
    )
    _fails(
        seeded,
        "INSERT INTO body_holders (body_id, body_kind, post_title, holder_name, valid_from,"
        " source_url) VALUES ('ccaa-13-gobierno', 'executive_head', ' ', 'N', '2023-6-17',"
        " 'https://example.org/s')",
        "body_holders_post_title_not_empty",
    )


# --- competences ---------------------------------------------------------------------


def _competence(db: Connection) -> int:
    return int(
        db.execute(
            text(
                "INSERT INTO body_competences (body_id, summary, legal_basis, source_url)"
                " VALUES ('ccaa-13-gobierno', 'Runs the public health service', 'EA art. 1', :s)"
                " RETURNING id"
            ),
            {"s": SOURCE},
        ).scalar_one()
    )


def test_a_competence_relates_to_a_sector_once(seeded: Connection) -> None:
    competence = _competence(seeded)
    seeded.execute(
        text("INSERT INTO body_competence_sectors VALUES (:c, 'health')"), {"c": competence}
    )

    _fails(
        seeded,
        "INSERT INTO body_competence_sectors VALUES (:c, 'health')",
        "body_competence_sectors_pkey",
        c=competence,
    )
    _fails(
        seeded,
        "INSERT INTO body_competence_sectors VALUES (:c, 'nowhere')",
        "body_competence_sectors_sector_id_fkey",
        c=competence,
    )


def test_a_competence_needs_a_summary_a_legal_basis_and_a_source_that_is_a_url(
    seeded: Connection,
) -> None:
    for column, value, constraint in [
        ("summary", "  ", "body_competences_summary_not_empty"),
        ("legal_basis", "", "body_competences_legal_basis_not_empty"),
        ("source_url", "x", "body_competences_source_is_url"),
    ]:
        values = {"summary": "S", "legal_basis": "L", "source_url": SOURCE} | {column: value}
        _fails(
            seeded,
            "INSERT INTO body_competences (body_id, summary, legal_basis, source_url)"
            " VALUES ('ccaa-13-gobierno', :summary, :legal_basis, :source_url)",
            constraint,
            **values,
        )
