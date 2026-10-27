import itertools
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url

from datos.stories.domain.grouping import group_stories
from datos.stories.domain.story import GroupingSettings
from datos.stories.infrastructure.pg_embedding_repository import PgEmbeddingRepository
from datos.stories.infrastructure.pg_story_repository import PgStoryRepository

pytestmark = pytest.mark.integration

_names = (f"stories_it_{n}" for n in itertools.count())
SINCE = datetime(2026, 10, 1, tzinfo=UTC)
SETTINGS = GroupingSettings(threshold=0.9, window_days=3)


def vector(*leading: float) -> list[float]:
    return [*leading, *([0.0] * (768 - len(leading)))]


@pytest.fixture
def engine(postgres_url: str) -> Iterator[Engine]:
    """A database per test: the repositories commit. Articles 1-4: see the helper below."""
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
        for outlet in ("outlet-a", "outlet-b"):
            connection.execute(
                text(
                    "INSERT INTO outlets (id, name, home_url, scope, region_id)"
                    " VALUES (:id, :id, 'https://x.example', 'national', NULL)"
                ),
                {"id": outlet},
            )
        # (outlet, day of October): 1 and 2 cover the same event, 3 is the same outlet as 1,
        # 4 is the same vector but ten days later.
        for number, (outlet, day) in enumerate(
            [("outlet-a", 10), ("outlet-b", 11), ("outlet-a", 11), ("outlet-b", 21)], start=1
        ):
            connection.execute(
                text(
                    "INSERT INTO articles (outlet_id, url, published_at, headline)"
                    " VALUES (:outlet, :url, :at, :headline)"
                ),
                {
                    "outlet": outlet,
                    "url": f"https://x.example/{number}",
                    "at": datetime(2026, 10, day, tzinfo=UTC),
                    "headline": f"Headline {number}",
                },
            )
    PgEmbeddingRepository(engine).add("encoder", "v1", [(n, vector(1.0)) for n in (1, 2, 3, 4)])
    yield engine
    engine.dispose()


def test_only_close_articles_of_different_outlets_inside_the_window_are_candidates(
    engine: Engine,
) -> None:
    pairs = PgStoryRepository(engine).candidate_pairs("v1", since=SINCE, settings=SETTINGS)

    assert [(p.article_a_id, p.article_b_id) for p in pairs] == [(1, 2), (2, 3)]
    assert all(p.similarity == pytest.approx(1.0) for p in pairs)
    assert pairs[0].days_apart == pytest.approx(1.0)


def test_the_threshold_filters_dissimilar_vectors(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE article_embeddings SET embedding = CAST(:v AS vector) WHERE article_id = 2"
            ),
            {"v": "[" + ",".join(["0.0", "1.0"] + ["0.0"] * 766) + "]"},
        )

    pairs = PgStoryRepository(engine).candidate_pairs("v1", since=SINCE, settings=SETTINGS)

    assert pairs == []


def test_a_run_is_stored_whole_and_a_second_run_does_not_touch_the_first(engine: Engine) -> None:
    repository = PgStoryRepository(engine)
    pairs = repository.candidate_pairs("v1", since=SINCE, settings=SETTINGS)
    stories = group_stories(pairs, SETTINGS)

    first = repository.add_run("v1", SETTINGS, stories, since=SINCE)
    second = repository.add_run("v1", SETTINGS, stories, since=SINCE)

    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT run_id, count(*) FROM story_articles GROUP BY run_id ORDER BY run_id")
        ).all()
    assert first != second
    assert [tuple(r) for r in rows] == [(first, 3), (second, 3)]


def test_the_run_records_how_far_back_it_read(engine: Engine) -> None:
    repository = PgStoryRepository(engine)
    stories = group_stories(
        repository.candidate_pairs("v1", since=SINCE, settings=SETTINGS), SETTINGS
    )

    run_id = repository.add_run("v1", SETTINGS, stories, since=SINCE)

    with engine.connect() as connection:
        stored = connection.execute(
            text("SELECT since FROM story_runs WHERE id = :id"), {"id": run_id}
        ).scalar_one()
    assert stored == SINCE


def test_the_encoder_version_is_the_one_with_most_embeddings_not_the_newest(engine: Engine) -> None:
    assert PgStoryRepository(engine).latest_encoder_version() == "v1"

    # A newer version that has only started covers one article: it must not win.
    PgEmbeddingRepository(engine).add("encoder", "v2", [(1, vector(1.0))])

    assert PgStoryRepository(engine).latest_encoder_version() == "v1"
