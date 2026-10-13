from collections.abc import Iterator

import pytest
from testcontainers.postgres import PostgresContainer

# Same image as docker-compose.yml, so tests see the same PostgreSQL and pgvector versions.
POSTGRES_IMAGE = "pgvector/pgvector:0.8.2-pg17"


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    with PostgresContainer(POSTGRES_IMAGE, driver="psycopg") as container:
        yield container.get_connection_url()
