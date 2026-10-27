import itertools
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url

from datos.stories.infrastructure.pg_embedding_repository import PgEmbeddingRepository

pytestmark = pytest.mark.integration

_names = (f"embeddings_it_{n}" for n in itertools.count())
SINCE = datetime(2026, 10, 1, tzinfo=UTC)
VECTOR = [0.1] * 768


@pytest.fixture
def engine(postgres_url: str) -> Iterator[Engine]:
    """A database per test: the repository commits."""
    name = next(_names)
    with create_engine(postgres_url, isolation_level="AUTOCOMMIT").connect() as admin:
        admin.execute(text(f"CREATE DATABASE {name}"))
    url = make_url(postgres_url).set(database=name).render_as_string(hide_password=False)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO territories (id, ine_code, name, level, parent_id)"
                " VALUES ('es', NULL, 'España', 'state', NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO outlets (id, name, home_url, scope, region_id)"
                " VALUES ('outlet-a', 'Outlet A', 'https://a.example', 'national', NULL)"
            )
        )
        for number, day in enumerate((15, 20, 2), start=1):
            connection.execute(
                text(
                    "INSERT INTO articles (outlet_id, url, published_at, headline, lead)"
                    " VALUES ('outlet-a', :url, :at, :headline, 'Lead')"
                ),
                {
                    "url": f"https://a.example/{number}",
                    "at": datetime(2026, 10 if day != 2 else 9, day, tzinfo=UTC),
                    "headline": f"Headline {number}",
                },
            )
    yield engine
    engine.dispose()


def test_missing_lists_recent_articles_newest_first(engine: Engine) -> None:
    missing = PgEmbeddingRepository(engine).missing("v1", since=SINCE, limit=10)

    assert [a.headline for a in missing] == ["Headline 2", "Headline 1"]


def test_an_embedded_article_is_no_longer_missing_for_that_version_only(engine: Engine) -> None:
    repository = PgEmbeddingRepository(engine)
    first = repository.missing("v1", since=SINCE, limit=10)[0].article_id

    assert repository.add("encoder", "v1", [(first, VECTOR)]) == 1

    assert first not in [a.article_id for a in repository.missing("v1", since=SINCE, limit=10)]
    assert first in [a.article_id for a in repository.missing("v2", since=SINCE, limit=10)]


def test_storing_the_same_vector_twice_adds_nothing(engine: Engine) -> None:
    repository = PgEmbeddingRepository(engine)
    article_id = repository.missing("v1", since=SINCE, limit=10)[0].article_id
    repository.add("encoder", "v1", [(article_id, VECTOR)])

    assert repository.add("encoder", "v1", [(article_id, VECTOR)]) == 0
