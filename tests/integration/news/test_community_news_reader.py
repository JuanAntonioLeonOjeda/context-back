from datetime import UTC, datetime, timedelta
from itertools import pairwise
from pathlib import Path

import pytest
from sqlalchemy import Connection, text

from datos.news.infrastructure.pg_news_reader import PgCommunityNewsReader
from datos.territories.csv_source import read_territories
from datos.territories.repository import PgTerritoryRepository

pytestmark = pytest.mark.integration

SINCE = datetime(2026, 9, 15, tzinfo=UTC)
UNTIL = datetime(2026, 11, 15, tzinfo=UTC)
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
    for outlet_id in ("outlet-a", "outlet-b"):
        db.execute(
            text(
                "INSERT INTO outlets (id, name, home_url, scope, region_id)"
                " VALUES (:id, :name, 'https://x.example', 'national', NULL)"
            ),
            {"id": outlet_id, "name": outlet_id.replace("-", " ").title()},
        )
    return db


def add_article(
    db: Connection, outlet_id: str, published_at: datetime, *, lead: str | None = None
) -> int:
    return int(
        db.execute(
            text(
                "INSERT INTO articles (outlet_id, url, published_at, headline, lead)"
                " VALUES (:outlet_id, :url, :at, 'A headline', :lead) RETURNING id"
            ),
            {
                "outlet_id": outlet_id,
                "url": f"https://x.example/{outlet_id}/{published_at.isoformat()}",
                "at": published_at,
                "lead": lead,
            },
        ).scalar_one()
    )


def classify(
    db: Connection,
    article_id: int,
    *,
    communities: list[str],
    sectors: list[str],
    levels: list[str] | None = None,
    model_id: str = "rules",
    model_version: str = "v1",
    created_at: datetime = DAY,
) -> None:
    db.execute(
        text(
            "INSERT INTO classifications (article_id, model_id, model_version, communities,"
            " sectors, levels, evidence, created_at) VALUES (:article_id, :model_id,"
            " :model_version, :communities, :sectors, :levels, '[]', :created_at)"
        ),
        {
            "article_id": article_id,
            "model_id": model_id,
            "model_version": model_version,
            "communities": communities,
            "sectors": sectors,
            "levels": levels or [],
            "created_at": created_at,
        },
    )


def recent(db: Connection, territory_id: str = CANARIAS, sector_id: str = "health") -> list[int]:
    articles = PgCommunityNewsReader(db).recent(
        territory_id=territory_id,
        sector_id=sector_id,
        since=SINCE,
        until=UNTIL,
        model_id="rules",
        per_outlet_per_day=5,
    )
    return [a.article_id for a in articles]


def test_returns_only_the_articles_of_that_community_and_sector(connection: Connection) -> None:
    match = add_article(connection, "outlet-a", DAY)
    other_sector = add_article(connection, "outlet-a", DAY + timedelta(minutes=1))
    other_community = add_article(connection, "outlet-a", DAY + timedelta(minutes=2))
    classify(connection, match, communities=[CANARIAS, MADRID], sectors=["health", "housing"])
    classify(connection, other_sector, communities=[CANARIAS], sectors=["housing"])
    classify(connection, other_community, communities=[MADRID], sectors=["health"])

    assert recent(connection) == [match]
    assert recent(connection, MADRID) == [other_community, match]


def test_the_latest_classification_of_the_active_classifier_wins(connection: Connection) -> None:
    relabelled_out = add_article(connection, "outlet-a", DAY)
    relabelled_in = add_article(connection, "outlet-a", DAY + timedelta(minutes=1))
    only_other_model = add_article(connection, "outlet-a", DAY + timedelta(minutes=2))
    later = DAY + timedelta(days=1)
    classify(connection, relabelled_out, communities=[CANARIAS], sectors=["health"])
    classify(
        connection, relabelled_out, communities=[], sectors=[], model_version="v2", created_at=later
    )
    classify(connection, relabelled_in, communities=[], sectors=[])
    classify(
        connection,
        relabelled_in,
        communities=[CANARIAS],
        sectors=["health"],
        model_version="v2",
        created_at=later,
    )
    classify(
        connection, only_other_model, communities=[CANARIAS], sectors=["health"], model_id="setfit"
    )

    assert recent(connection) == [relabelled_in]


def test_keeps_the_five_newest_per_outlet_newest_first_ties_by_outlet(
    connection: Connection,
) -> None:
    a = [add_article(connection, "outlet-a", DAY - timedelta(hours=h)) for h in range(7)]
    b = add_article(connection, "outlet-b", DAY)  # same time as a[0]
    for article_id in [*a, b]:
        classify(connection, article_id, communities=[CANARIAS], sectors=["health"])

    assert recent(connection) == [a[0], b, a[1], a[2], a[3], a[4]]


def test_leaves_out_what_was_published_before_the_window(connection: Connection) -> None:
    inside = add_article(connection, "outlet-a", SINCE)
    before = add_article(connection, "outlet-a", SINCE - timedelta(seconds=1))
    for article_id in (inside, before):
        classify(connection, article_id, communities=[CANARIAS], sectors=["health"])

    assert recent(connection) == [inside]


def test_maps_the_row_with_outlet_name_and_classifier(connection: Connection) -> None:
    article_id = add_article(connection, "outlet-a", DAY, lead="Never shown")
    classify(
        connection, article_id, communities=[CANARIAS], sectors=["health"], levels=["ccaa", "state"]
    )

    [article] = PgCommunityNewsReader(connection).recent(
        territory_id=CANARIAS,
        sector_id="health",
        since=SINCE,
        until=UNTIL,
        model_id="rules",
        per_outlet_per_day=5,
    )

    assert article.outlet_name == "Outlet A"
    assert (article.model_id, article.model_version) == ("rules", "v1")
    assert article.published_at == DAY
    assert "Never shown" not in repr(article)


def test_lists_the_active_sectors_of_the_database(connection: Connection) -> None:
    connection.execute(
        text("INSERT INTO sectors (id, name, is_active) VALUES ('work', 'Work', false)")
    )

    assert PgCommunityNewsReader(connection).sector_ids() == {"education", "health", "housing"}


def add_story_with_article(db: Connection, run_id: int, article_id: int) -> int:
    story_id = int(
        db.execute(
            text("INSERT INTO stories (run_id) VALUES (:run) RETURNING id"), {"run": run_id}
        ).scalar_one()
    )
    db.execute(
        text(
            "INSERT INTO story_articles (run_id, story_id, article_id, similarity)"
            " VALUES (:run, :story, :article, 0.9)"
        ),
        {"run": run_id, "story": story_id, "article": article_id},
    )
    return story_id


def tree_story_ids(db: Connection) -> dict[int, int | None]:
    articles = PgCommunityNewsReader(db).recent(
        territory_id=CANARIAS,
        sector_id="health",
        since=SINCE,
        until=UNTIL,
        model_id="rules",
        per_outlet_per_day=5,
    )
    return {a.article_id: a.tree_story_id for a in articles}


def test_an_item_names_the_story_whose_tree_it_belongs_to_and_only_then(
    connection: Connection,
) -> None:
    with_tree_child = add_article(connection, "outlet-a", DAY)
    with_tree_parent = add_article(connection, "outlet-b", DAY + timedelta(hours=1))
    lonely = add_article(connection, "outlet-a", DAY + timedelta(hours=2))
    for article_id in (with_tree_child, with_tree_parent, lonely):
        classify(connection, article_id, communities=[CANARIAS], sectors=["health"])
    run_id = int(
        connection.execute(
            text(
                "INSERT INTO story_runs (encoder_version, threshold, window_days)"
                " VALUES ('v1', 0.88, 3) RETURNING id"
            )
        ).scalar_one()
    )
    child = add_story_with_article(connection, run_id, with_tree_child)
    parent = add_story_with_article(connection, run_id, with_tree_parent)
    add_story_with_article(connection, run_id, lonely)
    assert set(tree_story_ids(connection).values()) == {None}  # no tree run yet
    tree_run = int(
        connection.execute(
            text(
                "INSERT INTO story_tree_runs (story_run_id, threshold, window_days)"
                " VALUES (:run, 0.75, 14) RETURNING id"
            ),
            {"run": run_id},
        ).scalar_one()
    )
    connection.execute(
        text(
            "INSERT INTO story_links (tree_run_id, story_run_id, story_id, parent_story_id,"
            " similarity) VALUES (:tree, :run, :child, :parent, 0.8)"
        ),
        {"tree": tree_run, "run": run_id, "child": child, "parent": parent},
    )

    assert tree_story_ids(connection) == {
        with_tree_child: child,
        with_tree_parent: parent,
        lonely: None,
    }


def build_trees(connection: Connection, chains: list[list[int]]) -> list[list[int]]:
    """One story per article in one grouping run and one tree run; each chain of articles is a
    tree whose stories are the child of the one before. Returns the story ids of each chain."""
    run_id = int(
        connection.execute(
            text(
                "INSERT INTO story_runs (encoder_version, threshold, window_days)"
                " VALUES ('v1', 0.88, 3) RETURNING id"
            )
        ).scalar_one()
    )
    stories = [[add_story_with_article(connection, run_id, a) for a in chain] for chain in chains]
    tree_run = int(
        connection.execute(
            text(
                "INSERT INTO story_tree_runs (story_run_id, threshold, window_days)"
                " VALUES (:run, 0.75, 14) RETURNING id"
            ),
            {"run": run_id},
        ).scalar_one()
    )
    for chain in stories:
        for parent, child in pairwise(chain):
            connection.execute(
                text(
                    "INSERT INTO story_links (tree_run_id, story_run_id, story_id,"
                    " parent_story_id, similarity) VALUES (:tree, :run, :child, :parent, 0.8)"
                ),
                {"tree": tree_run, "run": run_id, "child": child, "parent": parent},
            )
    return stories


def latest_per_tree(db: Connection) -> list[tuple[int, int | None]]:
    articles = PgCommunityNewsReader(db).latest_per_tree(
        territory_id=CANARIAS, sector_id="health", model_id="rules"
    )
    return [(a.article_id, a.tree_story_id) for a in articles]


def test_a_tree_is_listed_once_by_its_newest_article_in_the_community_and_sector_any_day(
    connection: Connection,
) -> None:
    oldest = add_article(connection, "outlet-a", DAY - timedelta(days=200))
    middle = add_article(connection, "outlet-b", DAY - timedelta(days=100))
    newest = add_article(connection, "outlet-a", DAY - timedelta(days=50))
    elsewhere = add_article(connection, "outlet-b", DAY)  # newer, but in another community
    for article_id in (oldest, middle, newest):
        classify(connection, article_id, communities=[CANARIAS], sectors=["health"])
    classify(connection, elsewhere, communities=[MADRID], sectors=["health"])
    [stories] = build_trees(connection, [[oldest, middle, newest, elsewhere]])

    assert latest_per_tree(connection) == [(newest, stories[2])]


def test_two_trees_are_two_items_newest_first_and_an_article_outside_any_tree_is_not_one(
    connection: Connection,
) -> None:
    older = [
        add_article(connection, "outlet-a", DAY - timedelta(days=30)),
        add_article(connection, "outlet-b", DAY - timedelta(days=29)),
    ]
    newer = [
        add_article(connection, "outlet-a", DAY - timedelta(days=2)),
        add_article(connection, "outlet-b", DAY - timedelta(days=1)),
    ]
    alone = add_article(connection, "outlet-a", DAY)
    for article_id in (*older, *newer, alone):
        classify(connection, article_id, communities=[CANARIAS], sectors=["health"])
    older_stories, newer_stories = build_trees(connection, [older, newer])

    assert latest_per_tree(connection) == [
        (newer[1], newer_stories[1]),
        (older[1], older_stories[1]),
    ]


def test_the_end_of_the_range_is_excluded_and_the_start_included(connection: Connection) -> None:
    first = add_article(connection, "outlet-a", DAY)
    last_second = add_article(connection, "outlet-a", DAY + timedelta(hours=1))
    at_the_end = add_article(connection, "outlet-a", DAY + timedelta(hours=2))
    for article_id in (first, last_second, at_the_end):
        classify(connection, article_id, communities=[CANARIAS], sectors=["health"])

    articles = PgCommunityNewsReader(connection).recent(
        territory_id=CANARIAS,
        sector_id="health",
        since=DAY,
        until=DAY + timedelta(hours=2),
        model_id="rules",
        per_outlet_per_day=5,
    )

    assert [a.article_id for a in articles] == [last_second, first]


def test_the_cap_is_per_outlet_and_per_day_in_spain_not_per_range(connection: Connection) -> None:
    today = [add_article(connection, "outlet-a", DAY + timedelta(minutes=m)) for m in range(7)]
    yesterday = [
        add_article(connection, "outlet-a", DAY - timedelta(days=1) + timedelta(minutes=m))
        for m in range(7)
    ]
    for article_id in [*today, *yesterday]:
        classify(connection, article_id, communities=[CANARIAS], sectors=["health"])

    assert recent(connection) == [*reversed(today[2:]), *reversed(yesterday[2:])]


def test_a_day_is_a_day_in_spain_not_in_utc(connection: Connection) -> None:
    # 22:30 UTC on the 10th is 00:30 on the 11th in Spain (CEST): a different day from 09:00 UTC.
    late = datetime(2026, 10, 10, 22, 30, tzinfo=UTC)
    morning = [add_article(connection, "outlet-a", DAY + timedelta(minutes=m)) for m in range(5)]
    after_midnight = add_article(connection, "outlet-a", late)
    for article_id in [*morning, after_midnight]:
        classify(connection, article_id, communities=[CANARIAS], sectors=["health"])

    assert after_midnight in recent(connection)
    assert len(recent(connection)) == 6
