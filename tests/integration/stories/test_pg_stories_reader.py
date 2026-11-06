from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import Connection, text

from datos.stories.infrastructure.pg_stories_reader import PgCommunityStoriesReader
from datos.territories.csv_source import read_territories
from datos.territories.repository import PgTerritoryRepository

pytestmark = pytest.mark.integration

SINCE = datetime(2026, 9, 15, tzinfo=UTC)
DAY = datetime(2026, 10, 10, 9, 0, tzinfo=UTC)
CANARIAS, MADRID = "ccaa-05", "ccaa-13"


@pytest.fixture
def connection(db: Connection) -> Connection:
    PgTerritoryRepository(db).upsert_all(read_territories(Path("data/territories/territories.csv")))
    db.execute(
        text(
            "INSERT INTO sectors (id, name) VALUES"
            " ('education', 'Education'), ('health', 'Health'), ('housing', 'Housing')"
        )
    )
    for outlet_id in ("outlet-a", "outlet-b", "outlet-c"):
        db.execute(
            text(
                "INSERT INTO outlets (id, name, home_url, scope, region_id)"
                " VALUES (:id, :id, 'https://x.example', 'national', NULL)"
            ),
            {"id": outlet_id},
        )
    return db


def add_article(
    db: Connection,
    outlet_id: str,
    *,
    communities: list[str],
    sectors: list[str],
    published_at: datetime = DAY,
) -> int:
    article_id = int(
        db.execute(
            text(
                "INSERT INTO articles (outlet_id, url, published_at, headline, lead)"
                " VALUES (:outlet_id, :url, :at, 'A headline', 'A private lead') RETURNING id"
            ),
            {
                "outlet_id": outlet_id,
                "url": f"https://x.example/{outlet_id}/{published_at.isoformat()}/{communities}",
                "at": published_at,
            },
        ).scalar_one()
    )
    classify(db, article_id, communities=communities, sectors=sectors)
    return article_id


def classify(
    db: Connection,
    article_id: int,
    *,
    communities: list[str],
    sectors: list[str],
    model_version: str = "v1",
    created_at: datetime = DAY,
) -> None:
    db.execute(
        text(
            "INSERT INTO classifications (article_id, model_id, model_version, communities,"
            " sectors, levels, evidence, created_at) VALUES (:article_id, 'rules',"
            " :model_version, :communities, :sectors, '{}', '[]', :created_at)"
        ),
        {
            "article_id": article_id,
            "model_version": model_version,
            "communities": communities,
            "sectors": sectors,
            "created_at": created_at,
        },
    )


def add_run(db: Connection, *, created_at: datetime = DAY) -> int:
    return int(
        db.execute(
            text(
                "INSERT INTO story_runs (encoder_version, threshold, window_days, created_at)"
                " VALUES ('v1', 0.88, 3, :created_at) RETURNING id"
            ),
            {"created_at": created_at},
        ).scalar_one()
    )


def add_story(db: Connection, run_id: int, article_ids: list[int]) -> int:
    story_id = int(
        db.execute(
            text("INSERT INTO stories (run_id) VALUES (:run_id) RETURNING id"), {"run_id": run_id}
        ).scalar_one()
    )
    for article_id in article_ids:
        db.execute(
            text(
                "INSERT INTO story_articles (run_id, story_id, article_id, similarity)"
                " VALUES (:run_id, :story_id, :article_id, 0.9)"
            ),
            {"run_id": run_id, "story_id": story_id, "article_id": article_id},
        )
    return story_id


def read(
    db: Connection, run_id: int, territory_id: str = CANARIAS, sector_id: str | None = None
) -> dict[int, list[int]]:
    stories = PgCommunityStoriesReader(db).stories(
        run_id=run_id, territory_id=territory_id, sector_id=sector_id, since=SINCE, model_id="rules"
    )
    return {s.story_id: [a.article_id for a in s.articles] for s in stories}


def test_a_story_whose_articles_mostly_name_the_community_is_returned(
    connection: Connection,
) -> None:
    run = add_run(connection)
    a = add_article(connection, "outlet-a", communities=[CANARIAS], sectors=["health"])
    b = add_article(connection, "outlet-b", communities=[CANARIAS], sectors=["health"])
    c = add_article(connection, "outlet-c", communities=[MADRID], sectors=["health"])
    story = add_story(connection, run, [a, b, c])

    assert read(connection, run) == {story: [a, b, c]}
    assert read(connection, run, territory_id=MADRID) == {}


def test_half_of_the_articles_is_not_a_majority(connection: Connection) -> None:
    run = add_run(connection)
    a = add_article(connection, "outlet-a", communities=[CANARIAS], sectors=["health"])
    b = add_article(connection, "outlet-b", communities=[MADRID], sectors=["health"])
    add_story(connection, run, [a, b])

    assert read(connection, run) == {}


def test_the_sector_is_only_checked_when_asked_for(connection: Connection) -> None:
    run = add_run(connection)
    a = add_article(connection, "outlet-a", communities=[CANARIAS], sectors=["health"])
    b = add_article(connection, "outlet-b", communities=[CANARIAS], sectors=["health"])
    story = add_story(connection, run, [a, b])

    assert read(connection, run, sector_id="health") == {story: [a, b]}
    assert read(connection, run, sector_id="housing") == {}
    assert read(connection, run, sector_id=None) == {story: [a, b]}


def test_a_story_with_nothing_published_in_the_window_is_left_out(connection: Connection) -> None:
    run = add_run(connection)
    old = SINCE - timedelta(days=1)
    a = add_article(connection, "outlet-a", communities=[CANARIAS], sectors=[], published_at=old)
    b = add_article(connection, "outlet-b", communities=[CANARIAS], sectors=[], published_at=old)
    add_story(connection, run, [a, b])

    assert read(connection, run) == {}


def test_the_latest_classification_decides_not_an_older_one(connection: Connection) -> None:
    run = add_run(connection)
    a = add_article(connection, "outlet-a", communities=[CANARIAS], sectors=[])
    b = add_article(connection, "outlet-b", communities=[CANARIAS], sectors=[])
    add_story(connection, run, [a, b])
    for article_id in (a, b):
        classify(
            connection,
            article_id,
            communities=[MADRID],
            sectors=[],
            model_version="v2",
            created_at=DAY + timedelta(days=1),
        )

    assert read(connection, run) == {}


def test_only_the_stories_of_the_asked_run_are_returned(connection: Connection) -> None:
    first, second = add_run(connection), add_run(connection)
    a = add_article(connection, "outlet-a", communities=[CANARIAS], sectors=[])
    b = add_article(connection, "outlet-b", communities=[CANARIAS], sectors=[])
    add_story(connection, first, [a, b])

    assert read(connection, second) == {}


def test_the_latest_run_is_the_newest_one(connection: Connection) -> None:
    reader = PgCommunityStoriesReader(connection)
    assert reader.latest_run() is None

    add_run(connection, created_at=DAY)
    newest = add_run(connection, created_at=DAY + timedelta(days=1))

    run = reader.latest_run()
    assert run is not None
    assert (run.run_id, run.window_days) == (newest, 3)
    assert run.threshold == pytest.approx(0.88)
