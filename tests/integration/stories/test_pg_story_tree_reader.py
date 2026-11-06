from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Connection, text

from datos.stories.domain.tree import StoryLink
from datos.stories.infrastructure.pg_story_tree_reader import PgStoryTreeReader

pytestmark = pytest.mark.integration

DAY = datetime(2026, 10, 10, 9, 0, tzinfo=UTC)


@pytest.fixture
def connection(db: Connection) -> Connection:
    db.execute(
        text(
            "INSERT INTO territories (id, ine_code, name, level, parent_id)"
            " VALUES ('es', NULL, 'España', 'state', NULL)"
        )
    )
    for outlet_id in ("outlet-a", "outlet-b"):
        db.execute(
            text(
                "INSERT INTO outlets (id, name, home_url, scope, region_id)"
                " VALUES (:id, :name, 'https://x.example', 'national', NULL)"
            ),
            {"id": outlet_id, "name": outlet_id.title()},
        )
    return db


def add_article(db: Connection, outlet_id: str, published_at: datetime) -> int:
    return int(
        db.execute(
            text(
                "INSERT INTO articles (outlet_id, url, published_at, headline, lead)"
                " VALUES (:outlet, :url, :at, 'A headline', 'A private lead') RETURNING id"
            ),
            {
                "outlet": outlet_id,
                "url": f"https://x.example/{outlet_id}/{published_at.isoformat()}",
                "at": published_at,
            },
        ).scalar_one()
    )


def add_run(db: Connection, created_at: datetime = DAY) -> int:
    return int(
        db.execute(
            text(
                "INSERT INTO story_runs (encoder_version, threshold, window_days, created_at)"
                " VALUES ('v1', 0.88, 3, :at) RETURNING id"
            ),
            {"at": created_at},
        ).scalar_one()
    )


def add_story(db: Connection, run_id: int, article_ids: list[int]) -> int:
    story_id = int(
        db.execute(
            text("INSERT INTO stories (run_id) VALUES (:run) RETURNING id"), {"run": run_id}
        ).scalar_one()
    )
    for article_id in article_ids:
        db.execute(
            text(
                "INSERT INTO story_articles (run_id, story_id, article_id, similarity)"
                " VALUES (:run, :story, :article, 0.9)"
            ),
            {"run": run_id, "story": story_id, "article": article_id},
        )
    return story_id


def add_tree_run(db: Connection, story_run_id: int, created_at: datetime = DAY) -> int:
    return int(
        db.execute(
            text(
                "INSERT INTO story_tree_runs (story_run_id, threshold, window_days, created_at)"
                " VALUES (:run, 0.75, 14, :at) RETURNING id"
            ),
            {"run": story_run_id, "at": created_at},
        ).scalar_one()
    )


def add_link(db: Connection, tree_run: int, story_run: int, child: int, parent: int) -> None:
    db.execute(
        text(
            "INSERT INTO story_links (tree_run_id, story_run_id, story_id, parent_story_id,"
            " similarity) VALUES (:tree, :run, :child, :parent, 0.8)"
        ),
        {"tree": tree_run, "run": story_run, "child": child, "parent": parent},
    )


def test_there_is_no_tree_run_until_one_is_stored(connection: Connection) -> None:
    assert PgStoryTreeReader(connection).latest_tree_run() is None


def test_the_latest_tree_run_carries_the_grouping_run_it_was_made_on(
    connection: Connection,
) -> None:
    old_run, new_run = add_run(connection), add_run(connection, DAY + timedelta(days=1))
    add_tree_run(connection, old_run)
    newest = add_tree_run(connection, new_run, DAY + timedelta(days=1))

    run = PgStoryTreeReader(connection).latest_tree_run()

    assert run is not None
    assert (run.tree_run_id, run.story_run.run_id, run.window_days) == (newest, new_run, 14)
    assert run.threshold == pytest.approx(0.75)
    assert run.story_run.threshold == pytest.approx(0.88)


def test_the_links_of_a_tree_run_are_returned_with_their_similarity(
    connection: Connection,
) -> None:
    run = add_run(connection)
    first, second = add_story(connection, run, []), add_story(connection, run, [])
    tree = add_tree_run(connection, run)
    add_link(connection, tree, run, second, first)

    assert PgStoryTreeReader(connection).links(tree) == [StoryLink(second, first, 0.8)]


def test_the_articles_of_a_story_come_by_outlet_and_never_with_the_lead(
    connection: Connection,
) -> None:
    run = add_run(connection)
    b = add_article(connection, "outlet-b", DAY)
    a = add_article(connection, "outlet-a", DAY + timedelta(hours=2))
    story = add_story(connection, run, [b, a])
    other = add_story(
        connection, run, [add_article(connection, "outlet-a", DAY + timedelta(days=1))]
    )

    articles = PgStoryTreeReader(connection).story_articles(run, [story])

    assert list(articles) == [story]
    assert [x.article_id for x in articles[story]] == [a, b]
    assert not hasattr(articles[story][0], "lead")
    assert other not in articles
