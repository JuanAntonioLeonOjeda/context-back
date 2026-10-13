import itertools
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url

from datos.indicators.application.load_indicators import (
    PublishedValue,
    SeriesValues,
    load_indicators,
)
from datos.indicators.domain.definitions import INDICATORS
from datos.indicators.domain.indicator import COMMUNITY_CODES, SeriesInfo
from datos.indicators.infrastructure.pg_repository import PgIndicatorRepository
from datos.territories.csv_source import read_territories
from datos.territories.repository import PgTerritoryRepository

pytestmark = pytest.mark.integration

AROPE = next(d for d in INDICATORS if d.id == "poverty_or_exclusion_rate")
_names = (f"indicators_it_{n}" for n in itertools.count())


@pytest.fixture
def engine(postgres_url: str) -> Iterator[Engine]:
    """A fresh database per test: the loader commits, and observations cannot be deleted."""
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


class Source:
    def __init__(self, value: str) -> None:
        self.value = value

    def series_of_table(self, table_id: str) -> list[SeriesInfo]:
        return [SeriesInfo(f"ECV{c}", c, dict(AROPE.selector)) for c in COMMUNITY_CODES]

    def series_values(self, series_code: str, *, last: int) -> SeriesValues:
        return SeriesValues(
            101,
            1,
            [PublishedValue(2025, 28, Decimal(self.value))],
            f"https://servicios.ine.es/wstempus/js/ES/DATOS_SERIE/{series_code}?nult={last}",
            "c" * 64,
        )


def _count(engine: Engine, sql: str) -> int:
    with engine.connect() as connection:
        return int(connection.execute(text(sql)).scalar_one())


def test_a_second_load_adds_nothing_and_each_row_has_its_download(engine: Engine) -> None:
    repository = PgIndicatorRepository(engine)

    first = load_indicators([AROPE], Source("30.1"), repository)
    second = load_indicators([AROPE], Source("30.1"), repository)

    assert (first, second) == (19, 0)
    assert _count(engine, "SELECT count(*) FROM downloads") == 19
    assert _count(engine, "SELECT count(*) FROM observations WHERE download_id IS NULL") == 0


def test_a_revision_and_a_return_to_the_old_value_each_add_a_row(engine: Engine) -> None:
    repository = PgIndicatorRepository(engine)

    for value in ("30.1", "29.9", "30.1"):  # A -> B -> A
        load_indicators([AROPE], Source(value), repository)

    assert _count(engine, "SELECT count(*) FROM observations") == 19 * 3
    assert repository.latest_values(AROPE.id, "ccaa-05") == {date(2025, 1, 1): Decimal("30.1")}


def test_values_keep_their_published_digits(engine: Engine) -> None:
    repository = PgIndicatorRepository(engine)

    load_indicators([AROPE], Source("34.7"), repository)

    assert repository.latest_values(AROPE.id, "ccaa-01")[date(2025, 1, 1)] == Decimal("34.7")
