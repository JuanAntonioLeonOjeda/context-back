from pathlib import Path

import pytest
from sqlalchemy import Connection

from datos.territories.csv_source import read_territories
from datos.territories.reader import PgTerritoryReader
from datos.territories.repository import PgTerritoryRepository
from datos.territories.territory import Level

pytestmark = pytest.mark.integration


def test_lists_the_19_communities_by_ine_code_without_the_state(db: Connection) -> None:
    PgTerritoryRepository(db).upsert_all(read_territories(Path("data/territories/territories.csv")))

    communities = PgTerritoryReader(db).by_level(Level.CCAA)

    assert len(communities) == 19
    assert [c.ine_code for c in communities] == [f"{n:02d}" for n in range(1, 20)]
    assert all(c.id != "es" for c in communities)
