import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.integration

INSERT = text(
    "INSERT INTO territories (id, ine_code, name, level, parent_id)"
    " VALUES (:id, :ine_code, :name, :level, :parent_id)"
)


def _row(
    id: str, ine_code: str | None, level: str, parent_id: str | None = None
) -> dict[str, str | None]:
    return {"id": id, "ine_code": ine_code, "name": "x", "level": level, "parent_id": parent_id}


def test_accepts_the_state_a_community_a_province_and_ceuta(
    migrated_postgres_url: str,
) -> None:
    engine = create_engine(migrated_postgres_url)
    with engine.connect() as connection:
        connection.execute(INSERT, _row("es", None, "state"))
        connection.execute(INSERT, _row("ccaa-13", "13", "ccaa", "es"))
        connection.execute(INSERT, _row("prov-28", "28", "province", "ccaa-13"))
        connection.execute(INSERT, _row("ccaa-18", "18", "ccaa", "es"))
        connection.rollback()  # leave the shared database clean for the other tests


@pytest.mark.parametrize(
    ("row", "possible_constraints"),
    [
        # Several constraints can reject the same row; PostgreSQL reports the first one it
        # evaluates (alphabetical by name), so we accept any of the constraints that apply.
        pytest.param(
            _row("pueblo-01", "01", "town"),
            {"territories_level_valid", "territories_id_matches_level"},
            id="unknown-level",
        ),
        pytest.param(
            _row("es", "01", "state"),
            {"territories_ine_code_by_level", "territories_id_ends_with_ine_code"},
            id="state-with-ine-code",
        ),
        pytest.param(
            _row("ccaa-01", None, "ccaa"),
            {"territories_ine_code_by_level"},
            id="community-without-ine-code",
        ),
        pytest.param(
            _row("city-18", "18", "autonomous_city"),
            {"territories_level_valid", "territories_id_matches_level"},
            id="autonomous-city-is-not-a-level",
        ),
        pytest.param(
            _row("ccaa-1", "1", "ccaa"),
            {"territories_ine_code_by_level", "territories_id_matches_level"},
            id="one-digit-ine-code",
        ),
        pytest.param(
            _row("prov-28", "28", "ccaa"),
            {"territories_id_matches_level"},
            id="province-id-used-as-community",
        ),
        pytest.param(
            _row("ccaa-13", "14", "ccaa"),
            {"territories_id_ends_with_ine_code"},
            id="id-and-ine-code-disagree",
        ),
    ],
)
def test_rejects_invalid_territories(
    migrated_postgres_url: str, row: dict[str, str | None], possible_constraints: set[str]
) -> None:
    engine = create_engine(migrated_postgres_url)
    with engine.connect() as connection, pytest.raises(IntegrityError) as error:
        connection.execute(INSERT, row)

    assert any(name in str(error.value) for name in possible_constraints)


def test_rejects_a_duplicate_territory(migrated_postgres_url: str) -> None:
    engine = create_engine(migrated_postgres_url)
    with engine.connect() as connection:
        connection.execute(INSERT, _row("ccaa-13", "13", "ccaa"))
        with pytest.raises(IntegrityError):
            connection.execute(INSERT, _row("ccaa-13", "13", "ccaa"))
        connection.rollback()
