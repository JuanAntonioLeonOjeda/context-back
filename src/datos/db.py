"""Database engine and the SQL implementation of the health probe."""

import structlog
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

log = structlog.get_logger(__name__)


def build_engine(database_url: str) -> Engine:
    # pool_pre_ping drops dead connections after a database restart.
    return create_engine(database_url, pool_pre_ping=True)


class SqlDatabaseProbe:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def is_reachable(self) -> bool:
        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError as error:
            log.warning("database_unreachable", error_type=type(error).__name__)
            return False
        return True
