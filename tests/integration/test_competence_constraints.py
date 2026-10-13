import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError

pytestmark = pytest.mark.integration

SOURCE = "https://www.boe.es/example"

INSERT = (
    "INSERT INTO competences"
    " (sector_id, activity, description, level, function, legal_basis, source_url)"
    " VALUES (:sector, :activity, 'd', :level, :function, 'basis', :source)"
)


@pytest.fixture
def seeded(db: Connection) -> Connection:
    db.execute(text("INSERT INTO sectors (id, name) VALUES ('housing', 'Housing')"))
    return db


def _competence(**overrides: str) -> dict[str, str]:
    values = {
        "sector": "housing",
        "activity": "public-housing",
        "level": "ccaa",
        "function": "execution",
        "source": SOURCE,
    }
    return values | overrides


def _rejected(db: Connection, params: dict[str, str]) -> str:
    with pytest.raises(DBAPIError) as error, db.begin_nested():
        db.execute(text(INSERT), params)
    return str(error.value)


def test_accepts_a_shared_competence_as_one_row_per_level(seeded: Connection) -> None:
    seeded.execute(text(INSERT), _competence(level="state", function="basic_legislation"))
    seeded.execute(text(INSERT), _competence(level="ccaa", function="development_legislation"))
    seeded.execute(text(INSERT), _competence(level="ccaa", function="execution"))
    seeded.execute(text(INSERT), _competence(level="local", function="execution"))


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        pytest.param({"level": "shared"}, "competences_level_valid", id="shared-is-not-a-level"),
        pytest.param({"level": "regional"}, "competences_level_valid", id="unknown-level"),
        pytest.param({"function": "funding"}, "competences_function_valid", id="unknown-function"),
        pytest.param(
            {"activity": "Public housing"}, "competences_activity_is_slug", id="activity-not-slug"
        ),
        pytest.param({"source": "BOE"}, "competences_source_is_url", id="source-not-url"),
        pytest.param({"sector": "transport"}, "competences_sector_id_fkey", id="unknown-sector"),
    ],
)
def test_rejects_invalid_competences(
    seeded: Connection, overrides: dict[str, str], constraint: str
) -> None:
    assert constraint in _rejected(seeded, _competence(**overrides))


def test_rejects_the_same_activity_level_and_function_twice(seeded: Connection) -> None:
    seeded.execute(text(INSERT), _competence())

    assert "competences_one_row_per_level_and_function" in _rejected(seeded, _competence())


def test_rejects_a_sector_whose_id_is_not_a_slug(db: Connection) -> None:
    with pytest.raises(DBAPIError) as error, db.begin_nested():
        db.execute(text("INSERT INTO sectors (id, name) VALUES ('Social Services', 'x')"))

    assert "sectors_id_is_slug" in str(error.value)
