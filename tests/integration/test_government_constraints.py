from datetime import date

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError, IntegrityError

pytestmark = pytest.mark.integration

SOURCE = "https://www.boe.es/example"


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
    db.execute(
        text(
            "INSERT INTO parties (id, name, short_name, colour_hex) VALUES"
            " ('party-a', 'Party A', 'PA', '#112233'),"
            " ('party-b', 'Party B', 'PB', '#445566')"
        )
    )
    return db


def _insert_term(db: Connection, territory_id: str, valid_from: date, valid_to: date | None) -> int:
    term_id = db.execute(
        text(
            "INSERT INTO government_terms"
            " (territory_id, president_name, valid_from, valid_to, source_url)"
            " VALUES (:territory_id, 'President', :valid_from, :valid_to, :source)"
            " RETURNING id"
        ),
        {
            "territory_id": territory_id,
            "valid_from": valid_from,
            "valid_to": valid_to,
            "source": SOURCE,
        },
    ).scalar_one()
    return int(term_id)


def _rejected(db: Connection, statement: str, params: dict[str, object]) -> str:
    """Run a statement that must fail; a savepoint keeps the test transaction usable."""
    with pytest.raises(DBAPIError) as error, db.begin_nested():
        db.execute(text(statement), params)
    return str(error.value)


# --- periods -------------------------------------------------------------------------


def test_accepts_consecutive_terms_where_one_ends_the_day_the_next_starts(
    seeded: Connection,
) -> None:
    _insert_term(seeded, "ccaa-13", date(2020, 1, 1), date(2023, 6, 17))
    _insert_term(seeded, "ccaa-13", date(2023, 6, 17), None)


def test_accepts_overlapping_terms_in_different_territories(seeded: Connection) -> None:
    _insert_term(seeded, "ccaa-13", date(2020, 1, 1), None)
    _insert_term(seeded, "ccaa-14", date(2020, 1, 1), None)
    _insert_term(seeded, "es", date(2020, 1, 1), None)


@pytest.mark.parametrize(
    ("first", "second"),
    [
        pytest.param(
            (date(2020, 1, 1), date(2023, 6, 18)), (date(2023, 6, 17), None), id="one-day-overlap"
        ),
        pytest.param((date(2020, 1, 1), None), (date(2023, 6, 17), None), id="two-in-force"),
        pytest.param(
            (date(2020, 1, 1), date(2024, 1, 1)),
            (date(2021, 1, 1), date(2022, 1, 1)),
            id="nested",
        ),
        pytest.param(
            (date(2020, 1, 1), date(2021, 1, 1)),
            (date(2020, 1, 1), date(2021, 1, 1)),
            id="duplicate",
        ),
    ],
)
def test_rejects_overlapping_terms_in_the_same_territory(
    seeded: Connection,
    first: tuple[date, date | None],
    second: tuple[date, date | None],
) -> None:
    _insert_term(seeded, "ccaa-13", *first)

    message = _rejected(
        seeded,
        "INSERT INTO government_terms"
        " (territory_id, president_name, valid_from, valid_to, source_url)"
        " VALUES ('ccaa-13', 'President', :valid_from, :valid_to, :source)",
        {"valid_from": second[0], "valid_to": second[1], "source": SOURCE},
    )

    assert "government_terms_no_overlap" in message


@pytest.mark.parametrize(
    ("territory_id", "valid_from", "valid_to", "source", "constraint"),
    [
        pytest.param(
            "prov-28",
            date(2020, 1, 1),
            None,
            SOURCE,
            "government_terms_territory_has_government",
            id="province",
        ),
        pytest.param(
            "ccaa-13",
            date(2020, 1, 1),
            date(2020, 1, 1),
            SOURCE,
            "government_terms_period_not_empty",
            id="zero-days",
        ),
        pytest.param(
            "ccaa-13",
            date(2020, 1, 2),
            date(2020, 1, 1),
            SOURCE,
            "government_terms_period_not_empty",
            id="ends-before-start",
        ),
        pytest.param(
            "ccaa-13",
            date(2020, 1, 1),
            None,
            "BOE 2020",
            "government_terms_source_is_url",
            id="source-not-url",
        ),
    ],
)
def test_rejects_invalid_terms(
    seeded: Connection,
    territory_id: str,
    valid_from: date,
    valid_to: date | None,
    source: str,
    constraint: str,
) -> None:
    message = _rejected(
        seeded,
        "INSERT INTO government_terms"
        " (territory_id, president_name, valid_from, valid_to, source_url)"
        " VALUES (:territory_id, 'President', :valid_from, :valid_to, :source)",
        {
            "territory_id": territory_id,
            "valid_from": valid_from,
            "valid_to": valid_to,
            "source": source,
        },
    )

    assert constraint in message


# --- parties of a term ---------------------------------------------------------------


def test_accepts_a_coalition_with_external_support(seeded: Connection) -> None:
    term_id = _insert_term(seeded, "es", date(2020, 1, 1), None)
    seeded.execute(
        text(
            "INSERT INTO government_term_parties (term_id, party_id, role, source_url) VALUES"
            " (:t, 'party-a', 'governing', :s), (:t, 'party-b', 'external_support', :s)"
        ),
        {"t": term_id, "s": SOURCE},
    )


def test_rejects_an_unknown_role(seeded: Connection) -> None:
    term_id = _insert_term(seeded, "es", date(2020, 1, 1), None)

    message = _rejected(
        seeded,
        "INSERT INTO government_term_parties (term_id, party_id, role, source_url)"
        " VALUES (:t, 'party-a', 'opposition', :s)",
        {"t": term_id, "s": SOURCE},
    )

    assert "government_term_parties_role_valid" in message


def test_rejects_the_same_party_twice_in_one_term(seeded: Connection) -> None:
    term_id = _insert_term(seeded, "es", date(2020, 1, 1), None)
    seeded.execute(
        text("INSERT INTO government_term_parties VALUES (:t, 'party-a', 'governing', :s)"),
        {"t": term_id, "s": SOURCE},
    )

    with pytest.raises(IntegrityError), seeded.begin_nested():
        seeded.execute(
            text(
                "INSERT INTO government_term_parties VALUES (:t, 'party-a', 'external_support', :s)"
            ),
            {"t": term_id, "s": SOURCE},
        )


# --- parties ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("party_id", "colour", "constraint"),
    [
        pytest.param("Party C", "#778899", "parties_id_is_slug", id="id-not-slug"),
        pytest.param("party-c", "#77889", "parties_colour_is_hex", id="short-colour"),
        pytest.param("party-c", "#77889G", "parties_colour_is_hex", id="not-hex"),
        pytest.param("party-c", "#77889A", "parties_colour_is_hex", id="uppercase-hex"),
    ],
)
def test_rejects_invalid_parties(
    seeded: Connection, party_id: str, colour: str, constraint: str
) -> None:
    message = _rejected(
        seeded,
        "INSERT INTO parties (id, name, short_name, colour_hex) VALUES (:id, 'C', 'C', :colour)",
        {"id": party_id, "colour": colour},
    )

    assert constraint in message


def test_rejects_a_party_role_without_a_url_source(seeded: Connection) -> None:
    term_id = _insert_term(seeded, "es", date(2020, 1, 1), None)

    message = _rejected(
        seeded,
        "INSERT INTO government_term_parties (term_id, party_id, role, source_url)"
        " VALUES (:t, 'party-a', 'governing', 'DSCD 15')",
        {"t": term_id},
    )

    assert "government_term_parties_source_is_url" in message
