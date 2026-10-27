import itertools
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url

from datos.stories.domain.tree import StoryLink, TreeSettings
from datos.stories.infrastructure.pg_embedding_repository import PgEmbeddingRepository
from datos.stories.infrastructure.pg_story_link_repository import PgStoryLinkRepository

pytestmark = pytest.mark.integration

_names = (f"links_it_{n}" for n in itertools.count())
SETTINGS = TreeSettings(threshold=0.9, window_days=14)


def vector(*leading: float) -> list[float]:
    return [*leading, *([0.0] * (768 - len(leading)))]


@pytest.fixture
def engine(postgres_url: str) -> Iterator[Engine]:
    """A database per test. Stories: 1 (days 1-2) and 2 (day 5) alike, 3 (day 6) unlike, 4 (day 30)
    alike but outside the window. Each story has two articles."""
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
                " VALUES ('outlet-a', 'A', 'https://a.example', 'national', NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO story_runs (encoder_version, threshold, window_days)"
                " VALUES ('v1', 0.88, 3)"
            )
        )
        for _ in range(4):
            connection.execute(text("INSERT INTO stories (run_id) VALUES (1)"))
        # (story, day, leading vector components)
        plan = [
            (1, 1, (1.0, 0.0)),
            (1, 2, (1.0, 0.0)),
            (2, 5, (1.0, 0.1)),
            (2, 5, (1.0, 0.1)),
            (3, 6, (0.0, 1.0)),
            (3, 6, (0.0, 1.0)),
            (4, 30, (1.0, 0.0)),
            (4, 30, (1.0, 0.0)),
        ]
        article_ids = []
        for number, (story, day, _) in enumerate(plan, start=1):
            month = 10 if day <= 31 else 11
            article_id = connection.execute(
                text(
                    "INSERT INTO articles (outlet_id, url, published_at, headline)"
                    " VALUES ('outlet-a', :url, :at, 'H') RETURNING id"
                ),
                {
                    "url": f"https://a.example/{number}",
                    "at": datetime(2026, month, day, tzinfo=UTC),
                },
            ).scalar_one()
            article_ids.append(article_id)
            connection.execute(
                text(
                    "INSERT INTO story_articles (run_id, story_id, article_id, similarity)"
                    " VALUES (1, :story, :article, 0.9)"
                ),
                {"story": story, "article": article_id},
            )
    PgEmbeddingRepository(engine).add(
        "encoder", "v1", [(i, vector(*plan[n][2])) for n, i in enumerate(article_ids)]
    )
    yield engine
    engine.dispose()


def test_the_latest_story_run_is_found(engine: Engine) -> None:
    assert PgStoryLinkRepository(engine).latest_story_run_id() == 1


def test_only_alike_stories_inside_the_window_are_paired(engine: Engine) -> None:
    pairs = PgStoryLinkRepository(engine).story_pairs(1, SETTINGS)

    assert [(p.first.story_id, p.second.story_id) for p in pairs] == [(1, 2)]
    assert pairs[0].similarity > 0.99
    assert pairs[0].first.started_at == datetime(2026, 10, 1, tzinfo=UTC)


def test_a_tree_run_is_stored_whole_and_a_second_run_leaves_the_first(engine: Engine) -> None:
    repository = PgStoryLinkRepository(engine)
    links = [StoryLink(2, 1, 0.99)]

    first = repository.add_run(1, SETTINGS, links)
    second = repository.add_run(1, SETTINGS, links)

    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT tree_run_id, count(*) FROM story_links GROUP BY 1 ORDER BY 1")
        ).all()
    assert first != second
    assert [tuple(r) for r in rows] == [(first, 1), (second, 1)]


def test_a_run_with_no_links_is_still_a_run(engine: Engine) -> None:
    repository = PgStoryLinkRepository(engine)

    run_id = repository.add_run(1, SETTINGS, [])

    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM story_tree_runs")).scalar() == 1
    assert run_id == 1
