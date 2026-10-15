import pytest

from datos.db import SqlDatabaseProbe, build_engine

pytestmark = pytest.mark.integration


def test_probe_reports_a_running_database_as_reachable(postgres_url: str) -> None:
    assert SqlDatabaseProbe(build_engine(postgres_url)).is_reachable() is True
