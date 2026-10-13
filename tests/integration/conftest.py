from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, create_engine
from testcontainers.community.postgres import PostgresContainer

# Same image as docker-compose.yml, so tests see the same PostgreSQL and pgvector versions.
POSTGRES_IMAGE = "pgvector/pgvector:0.8.2-pg17"


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    with PostgresContainer(POSTGRES_IMAGE, driver="psycopg") as container:
        yield container.get_connection_url()


@pytest.fixture(scope="session")
def migrated_postgres_url(postgres_url: str) -> str:
    """The container database with every migration applied."""
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", postgres_url)
    command.upgrade(config, "head")
    return postgres_url


@pytest.fixture
def db(migrated_postgres_url: str) -> Iterator[Connection]:
    """A connection inside a transaction that is rolled back after the test."""
    engine = create_engine(migrated_postgres_url)
    with engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        transaction.rollback()
