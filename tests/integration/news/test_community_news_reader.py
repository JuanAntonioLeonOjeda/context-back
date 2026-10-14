from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import Connection, text

from datos.governments.domain.competence import CompetenceLevel
from datos.news.infrastructure.pg_news_reader import PgCommunityNewsReader
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
        model_id="rules",
        per_outlet=5,
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


def test_maps_the_row_with_outlet_name_levels_and_classifier(connection: Connection) -> None:
    article_id = add_article(connection, "outlet-a", DAY, lead="Never shown")
    classify(
        connection, article_id, communities=[CANARIAS], sectors=["health"], levels=["ccaa", "state"]
    )

    [article] = PgCommunityNewsReader(connection).recent(
        territory_id=CANARIAS, sector_id="health", since=SINCE, model_id="rules", per_outlet=5
    )

    assert article.outlet_name == "Outlet A"
    assert article.levels == {CompetenceLevel.CCAA, CompetenceLevel.STATE}
    assert (article.model_id, article.model_version) == ("rules", "v1")
    assert article.published_at == DAY
    assert "Never shown" not in repr(article)


def test_lists_the_sectors_of_the_database(connection: Connection) -> None:
    assert PgCommunityNewsReader(connection).sector_ids() == {"education", "health", "housing"}
