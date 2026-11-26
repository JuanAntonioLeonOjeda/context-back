import itertools
import math
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.engine import make_url

from datos.stories.domain.related import RelatedSettings
from datos.stories.infrastructure.pg_embedding_repository import PgEmbeddingRepository
from datos.stories.infrastructure.pg_related_reader import PgRelatedReader

pytestmark = pytest.mark.integration

_names = (f"related_it_{n}" for n in itertools.count())
SETTINGS = RelatedSettings()
STEP_AT = datetime(2026, 11, 16, 12, tzinfo=UTC)
ORIGIN = (0.8, 0.6)  # the vector of the item the chain starts from (article 1)


def _unit(x: float, y: float) -> list[float]:
    return [x, y, *([0.0] * 766)]


def _similar(cosine: float) -> list[float]:
    """A unit vector whose cosine with (1, 0) is `cosine`."""
    return _unit(cosine, math.sqrt(1 - cosine**2))


@pytest.fixture
def engine(postgres_url: str) -> Iterator[Engine]:
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
                " VALUES ('abc', 'abc', 'https://x.example', 'national', NULL)"
            )
        )
    yield engine
    engine.dispose()


def _article(engine: Engine, number: int, at: datetime, vector: list[float] | None) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO articles (id, outlet_id, url, published_at, headline)"
                " OVERRIDING SYSTEM VALUE VALUES (:id, 'abc', :url, :at, :headline)"
            ),
            {
                "id": number,
                "url": f"https://x.example/{number}",
                "at": at,
                "headline": f"H{number}",
            },
        )
    if vector is not None:
        PgEmbeddingRepository(engine).add("encoder", "v1", [(number, vector)])


def _reader(engine: Engine) -> PgRelatedReader:
    # The API builds the reader on a request's connection; a test gives it one of its own.
    return PgRelatedReader(engine.connect())


def _ids(engine: Engine, step: int = 2, origin: int = 1, **kwargs: int) -> list[int]:
    candidates = _reader(engine).candidates(step, origin, SETTINGS, **kwargs)
    return [c.item.article_id for c in candidates]


def test_the_candidates_are_the_earlier_items_most_similar_first(engine: Engine) -> None:
    _article(engine, 1, STEP_AT + timedelta(days=1), _unit(*ORIGIN))
    _article(engine, 2, STEP_AT, _unit(1, 0))  # the step
    _article(engine, 3, STEP_AT - timedelta(days=1), _similar(0.75))
    _article(engine, 4, STEP_AT - timedelta(days=2), _similar(0.95))
    _article(engine, 5, STEP_AT + timedelta(hours=1), _similar(0.99))  # later than the step

    assert _ids(engine) == [4, 3]


def test_an_item_below_the_step_threshold_is_not_a_candidate(engine: Engine) -> None:
    _article(engine, 1, STEP_AT, _unit(*ORIGIN))
    _article(engine, 2, STEP_AT, _unit(1, 0))
    # Vectors are stored as float4: a cosine of exactly 0.70 comes back as 0.6999..., so the edge
    # itself is pinned by the domain's tests and here one value is on each side of it.
    _article(engine, 3, STEP_AT - timedelta(days=1), _similar(0.71))
    _article(engine, 4, STEP_AT - timedelta(days=1), _similar(0.69))

    assert _ids(engine) == [3]


def test_the_window_includes_its_first_instant_and_not_one_second_more(engine: Engine) -> None:
    _article(engine, 1, STEP_AT, _unit(*ORIGIN))
    _article(engine, 2, STEP_AT, _unit(1, 0))
    _article(engine, 3, STEP_AT - timedelta(days=14), _similar(0.9))
    _article(engine, 4, STEP_AT - timedelta(days=14, seconds=1), _similar(0.9))

    assert _ids(engine) == [3]


def test_each_candidate_carries_its_similarity_to_the_step_and_to_the_origin(
    engine: Engine,
) -> None:
    _article(engine, 1, STEP_AT + timedelta(days=1), _unit(*ORIGIN))
    _article(engine, 2, STEP_AT, _unit(1, 0))
    _article(engine, 3, STEP_AT - timedelta(days=1), _similar(0.8))

    [candidate] = _reader(engine).candidates(2, 1, SETTINGS)

    assert candidate.similarity == pytest.approx(0.8, abs=1e-5)
    # (0.8, 0.6) · (0.8, 0.6) = 1: this candidate points the same way as the origin.
    assert candidate.to_origin == pytest.approx(1.0, abs=1e-5)
    assert (candidate.item.outlet_id, candidate.item.headline) == ("abc", "H3")


def test_at_most_the_limit_of_candidates_comes_back(engine: Engine) -> None:
    _article(engine, 1, STEP_AT, _unit(*ORIGIN))
    _article(engine, 2, STEP_AT, _unit(1, 0))
    for number, cosine in zip(range(3, 8), (0.99, 0.95, 0.9, 0.85, 0.8), strict=True):
        _article(engine, number, STEP_AT - timedelta(hours=number), _similar(cosine))

    assert _ids(engine, limit=2) == [3, 4]


def test_a_step_with_no_vector_yet_has_no_candidates(engine: Engine) -> None:
    _article(engine, 1, STEP_AT, _unit(*ORIGIN))
    _article(engine, 2, STEP_AT, None)  # the worker has not embedded it yet
    _article(engine, 3, STEP_AT - timedelta(days=1), _similar(0.9))

    assert _ids(engine) == []


def test_an_article_is_read_back_and_an_unknown_one_is_none(engine: Engine) -> None:
    _article(engine, 1, STEP_AT, None)

    item = _reader(engine).news_item(1)

    assert item is not None and (item.article_id, item.outlet_id, item.headline) == (1, "abc", "H1")
    assert (item.outlet_name, item.url) == ("abc", "https://x.example/1")
    assert item.published_at == STEP_AT
    assert _reader(engine).news_item(999) is None


def test_the_encoder_version_is_read_once_per_reader(engine: Engine) -> None:
    _article(engine, 1, STEP_AT, _unit(*ORIGIN))
    _article(engine, 2, STEP_AT, _unit(1, 0))
    _article(engine, 3, STEP_AT - timedelta(days=1), _similar(0.9))
    connection = engine.connect()
    statements: list[str] = []
    event.listen(connection, "before_cursor_execute", lambda *args: statements.append(args[2]))
    reader = PgRelatedReader(connection)

    reader.candidates(2, 1, SETTINGS)
    reader.candidates(3, 1, SETTINGS)

    assert sum("GROUP BY encoder_version" in s for s in statements) == 1
