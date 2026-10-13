from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import Connection, text

from datos.governments.application.load_governments import load_governments
from datos.governments.infrastructure.csv_source import read_parties, read_terms
from datos.governments.infrastructure.pg_repository import PgGovernmentRepository
from datos.territories.csv_source import read_territories
from datos.territories.repository import PgTerritoryRepository

pytestmark = pytest.mark.integration

DATA = Path("data/governments")
SINCE = date(2020, 1, 1)
TODAY = date(2026, 10, 13)


def _load(db: Connection) -> None:
    PgTerritoryRepository(db).upsert_all(read_territories(Path("data/territories/territories.csv")))
    parties = read_parties(DATA / "parties.csv")
    terms = read_terms(DATA / "government_terms.csv", DATA / "government_term_parties.csv")
    load_governments(PgGovernmentRepository(db), parties, terms, since=SINCE, today=TODAY)


def _count(db: Connection, table: str) -> int:
    return int(db.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())  # noqa: S608


def test_loads_the_versioned_dataset_and_a_second_load_changes_nothing(db: Connection) -> None:
    _load(db)
    first = (
        _count(db, "parties"),
        _count(db, "government_terms"),
        _count(db, "government_term_parties"),
    )

    _load(db)
    second = (
        _count(db, "parties"),
        _count(db, "government_terms"),
        _count(db, "government_term_parties"),
    )

    assert first == second
    assert first[0] == 34
    assert first[1] == 93


def test_every_territory_with_a_government_is_covered_today(db: Connection) -> None:
    _load(db)

    uncovered = db.execute(
        text(
            """
            SELECT t.id FROM territories t
            WHERE t.level IN ('state', 'ccaa')
              AND NOT EXISTS (
                SELECT 1 FROM government_terms g
                WHERE g.territory_id = t.id
                  AND daterange(g.valid_from, g.valid_to, '[)') @> :today ::date)
            """
        ),
        {"today": TODAY},
    ).all()

    assert uncovered == []


def test_who_governed_madrid_on_the_day_of_a_handover(db: Connection) -> None:
    _load(db)

    def president_on(day: date) -> str:
        return str(
            db.execute(
                text(
                    "SELECT president_name FROM government_terms WHERE territory_id = 'es'"
                    " AND daterange(valid_from, valid_to, '[)') @> :day ::date"
                ),
                {"day": day},
            ).scalar_one()
        )

    assert president_on(date(2023, 11, 16)) == "Pedro Sánchez Pérez-Castejón"
    assert president_on(date(2024, 6, 1)) == "Pedro Sánchez Pérez-Castejón"


def test_a_failed_load_leaves_the_previous_data_untouched(db: Connection) -> None:
    _load(db)
    parties = read_parties(DATA / "parties.csv")
    terms = read_terms(DATA / "government_terms.csv", DATA / "government_term_parties.csv")

    with pytest.raises(Exception, match="problem"):
        load_governments(PgGovernmentRepository(db), parties, terms[:-1], since=SINCE, today=TODAY)

    assert _count(db, "government_terms") == 93
