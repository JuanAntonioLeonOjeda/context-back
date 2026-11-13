"""Municipal income stored with its download; the latest download wins; nothing is overwritten."""

import itertools
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, make_url, text

from datos.territories.csv_source import read_territories
from datos.territories.repository import PgTerritoryRepository
from datos.voters.application.load_income import IncomeDownload, load_income
from datos.voters.domain.income import MunicipalIncome
from datos.voters.infrastructure.pg_income_repository import PgIncomeRepository

pytestmark = pytest.mark.integration

_names = (f"income_it_{n}" for n in itertools.count())


@pytest.fixture
def engine(postgres_url: str) -> Iterator[Engine]:
    """A fresh database per test: the loader commits, and income rows cannot be deleted."""
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


class _Source:
    def __init__(self, euros: str) -> None:
        self.euros = euros

    def incomes(self, year: int) -> IncomeDownload:
        incomes = [MunicipalIncome("02003", year, Decimal(self.euros), "ADRH103921")]
        url = f"https://servicios.ine.es/wstempus/js/ES/DATOS_METADATAOPERACION/353?date={year}0101"
        return IncomeDownload(url, "d" * 64, incomes)


def _rows(engine: Engine) -> list[tuple[object, ...]]:
    with engine.connect() as connection:
        return [
            tuple(r)
            for r in connection.execute(
                text(
                    "SELECT i.municipality_code, i.province_id, i.euros_per_person, d.url"
                    " FROM municipal_income i JOIN downloads d ON d.id = i.download_id"
                    " ORDER BY i.id"
                )
            )
        ]


def test_a_second_load_with_the_same_values_adds_nothing(engine: Engine) -> None:
    repository = PgIncomeRepository(engine)

    assert load_income(_Source("14611"), repository, year=2023) == 1
    assert load_income(_Source("14611"), repository, year=2023) == 0

    [row] = _rows(engine)
    assert row[:3] == ("02003", "prov-02", Decimal("14611.00"))
    assert str(row[3]).endswith("DATOS_METADATAOPERACION/353?date=20230101")


def test_a_revision_is_a_new_row_and_becomes_the_latest(engine: Engine) -> None:
    repository = PgIncomeRepository(engine)
    load_income(_Source("14611"), repository, year=2023)

    assert load_income(_Source("14700"), repository, year=2023) == 1

    assert len(_rows(engine)) == 2
    assert repository.latest_incomes(2023) == {"02003": Decimal("14700.00")}
