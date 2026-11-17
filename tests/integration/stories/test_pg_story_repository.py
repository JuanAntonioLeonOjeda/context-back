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


def _article(engine: Engine, number: int, outlet: str, at: datetime) -> None:
    """One more article with the same vector as articles 1-4."""
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO articles (id, outlet_id, url, published_at, headline)"
                " OVERRIDING SYSTEM VALUE VALUES (:id, :outlet, :url, :at, 'Headline')"
            ),
            {"id": number, "outlet": outlet, "url": f"https://x.example/{number}", "at": at},
        )
    PgEmbeddingRepository(engine).add("encoder", "v1", [(number, vector(1.0))])


def _pairs(engine: Engine) -> list[tuple[int, int]]:
    pairs = PgStoryRepository(engine).candidate_pairs("v1", since=SINCE, settings=SETTINGS)
    return [(p.article_a_id, p.article_b_id) for p in pairs]


def test_the_window_includes_its_last_instant_and_not_one_second_more(engine: Engine) -> None:
    # Article 4 (outlet b) is on 21 October at 00:00: 3 days before is in, a second more is out.
    _article(engine, 10, "outlet-a", datetime(2026, 10, 18, tzinfo=UTC))
    _article(engine, 11, "outlet-a", datetime(2026, 10, 17, 23, 59, 59, tzinfo=UTC))

    assert (4, 10) in _pairs(engine)
    assert (4, 11) not in _pairs(engine)


def test_two_articles_of_the_same_instant_are_one_pair(engine: Engine) -> None:
    _article(engine, 10, "outlet-a", datetime(2026, 10, 25, tzinfo=UTC))
    _article(engine, 11, "outlet-b", datetime(2026, 10, 25, tzinfo=UTC))

    assert _pairs(engine).count((10, 11)) == 1


def test_an_earlier_article_with_a_later_id_keeps_the_smaller_id_and_its_outlet_first(
    engine: Engine,
) -> None:
    # Article 10 is published before article 2 (outlet b, 11 October) but has the bigger id.
    _article(engine, 10, "outlet-a", datetime(2026, 10, 10, 12, tzinfo=UTC))

    pairs = PgStoryRepository(engine).candidate_pairs("v1", since=SINCE, settings=SETTINGS)
    pair = next(p for p in pairs if (p.article_a_id, p.article_b_id) == (2, 10))
    assert (pair.outlet_a_id, pair.outlet_b_id) == ("outlet-b", "outlet-a")
    assert pair.days_apart == pytest.approx(0.5)


def test_an_article_before_the_start_is_not_paired_with_one_after_it(engine: Engine) -> None:
    _article(engine, 10, "outlet-b", datetime(2026, 9, 30, 23, tzinfo=UTC))
    _article(engine, 11, "outlet-a", datetime(2026, 10, 1, 1, tzinfo=UTC))

    assert (10, 11) not in _pairs(engine)


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
