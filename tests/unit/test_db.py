from sqlalchemy import create_engine

from datos.db import SqlDatabaseProbe


def test_probe_reports_unreachable_instead_of_raising() -> None:
    # Port 1 on localhost: nothing listens there, so the connection fails fast.
    engine = create_engine(
        "postgresql+psycopg://u:p@127.0.0.1:1/x", connect_args={"connect_timeout": 1}
    )

    assert SqlDatabaseProbe(engine).is_reachable() is False
