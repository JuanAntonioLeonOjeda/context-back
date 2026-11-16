"""A fresh database per test for the voters loaders: they commit, and values cannot be deleted."""

import itertools
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, make_url, text

from datos.territories.csv_source import read_territories
from datos.territories.repository import PgTerritoryRepository

_names = (f"values_it_{n}" for n in itertools.count())


@pytest.fixture
def engine(postgres_url: str) -> Iterator[Engine]:
    """A migrated database with the territories, new for every test."""
    name = next(_names)
    with create_engine(postgres_url, isolation_level="AUTOCOMMIT").connect() as admin:
        admin.execute(text(f"CREATE DATABASE {name}"))
    url = make_url(postgres_url).set(database=name).render_as_string(hide_password=False)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    engine = create_engine(url)
    with engine.begin() as connection:
        PgTerritoryRepository(connection).upsert_all(
            read_territories(Path("data/territories/territories.csv"))
        )
    yield engine
    engine.dispose()
