from pathlib import Path

import pytest
from sqlalchemy import Connection, text

from datos.territories.csv_source import read_territories
from datos.territories.repository import PgTerritoryRepository

pytestmark = pytest.mark.integration

REAL_CSV = Path("data/territories/territories.csv")


def _count_by_level(db: Connection) -> dict[str, int]:
    rows = db.execute(text("SELECT level, count(*) FROM territories GROUP BY level")).all()
    return {level: count for level, count in rows}


def test_loads_the_versioned_file_and_a_second_load_changes_nothing(db: Connection) -> None:
    repository = PgTerritoryRepository(db)
    territories = read_territories(REAL_CSV)

    repository.upsert_all(territories)
    repository.upsert_all(territories)

    assert _count_by_level(db) == {"state": 1, "ccaa": 19, "province": 52}


def test_madrid_province_hangs_from_the_community_of_madrid(db: Connection) -> None:
    PgTerritoryRepository(db).upsert_all(read_territories(REAL_CSV))

    parent = db.execute(text("SELECT parent_id FROM territories WHERE id = 'prov-28'")).scalar()

    assert parent == "ccaa-13"
