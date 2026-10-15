from datetime import UTC, datetime

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError

pytestmark = pytest.mark.integration

INSERT_OUTLET = (
    "INSERT INTO outlets (id, name, home_url, scope, region_id)"
    " VALUES (:id, 'Outlet', :home_url, :scope, :region_id)"
)
INSERT_ARTICLE = (
    "INSERT INTO articles (outlet_id, url, published_at, headline, lead)"
    " VALUES ('outlet-a', :url, :published_at, :headline, :lead)"
)
PUBLISHED_AT = datetime(2026, 10, 1, 8, 30, tzinfo=UTC)


@pytest.fixture
def seeded(db: Connection) -> Connection:
    db.execute(
        text(
            "INSERT INTO territories (id, ine_code, name, level, parent_id) VALUES"
            " ('es', NULL, 'España', 'state', NULL),"
            " ('ccaa-13', '13', 'Community A', 'ccaa', 'es'),"
            " ('prov-28', '28', 'Province A', 'province', 'ccaa-13')"
        )
    )
    db.execute(
        text(INSERT_OUTLET),
        {"id": "outlet-a", "home_url": "https://a.example", "scope": "national", "region_id": None},
    )
    return db


def _rejected(db: Connection, statement: str, params: dict[str, object]) -> str:
    with pytest.raises(DBAPIError) as error, db.begin_nested():
        db.execute(text(statement), params)
    return str(error.value)


def _outlet(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "id": "outlet-b",
        "home_url": "https://b.example",
        "scope": "regional",
        "region_id": "ccaa-13",
    }
    return values | overrides


def _article(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "url": "https://a.example/news/1",
        "published_at": PUBLISHED_AT,
        "headline": "Headline",
        "lead": "Short lead.",
    }
    return values | overrides


def test_accepts_a_regional_outlet_and_an_article_without_lead(seeded: Connection) -> None:
    seeded.execute(text(INSERT_OUTLET), _outlet())
    seeded.execute(text(INSERT_ARTICLE), _article(lead=None))


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        pytest.param(
            {"region_id": None}, "outlets_region_matches_scope", id="regional-without-region"
        ),
        pytest.param(
            {"scope": "national"}, "outlets_region_matches_scope", id="national-with-region"
        ),
        pytest.param(
            {"region_id": "prov-28"}, "outlets_region_matches_scope", id="region-is-a-province"
        ),
        pytest.param({"scope": "local"}, "outlets_region_matches_scope", id="unknown-scope"),
        pytest.param({"id": "Outlet B"}, "outlets_id_is_slug", id="id-not-slug"),
        pytest.param({"home_url": "b.example"}, "outlets_home_url_is_url", id="home-not-url"),
    ],
)
def test_rejects_invalid_outlets(
    seeded: Connection, overrides: dict[str, object], constraint: str
) -> None:
    assert constraint in _rejected(seeded, INSERT_OUTLET, _outlet(**overrides))


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        pytest.param({"url": "/news/1"}, "articles_url_is_url", id="relative-url"),
        pytest.param({"headline": "   "}, "articles_headline_not_blank", id="blank-headline"),
        pytest.param({"lead": "x" * 1001}, "articles_lead_is_short", id="body-instead-of-lead"),
        pytest.param({"published_at": None}, "published_at", id="no-publication-date"),
    ],
)
def test_rejects_invalid_articles(
    seeded: Connection, overrides: dict[str, object], constraint: str
) -> None:
    assert constraint in _rejected(seeded, INSERT_ARTICLE, _article(**overrides))


def test_rejects_the_same_url_twice_for_one_outlet(seeded: Connection) -> None:
    seeded.execute(text(INSERT_ARTICLE), _article())

    assert "articles_one_row_per_url" in _rejected(seeded, INSERT_ARTICLE, _article())


def test_accepts_the_same_url_in_two_outlets(seeded: Connection) -> None:
    seeded.execute(text(INSERT_OUTLET), _outlet())
    seeded.execute(text(INSERT_ARTICLE), _article())
    seeded.execute(
        text(
            "INSERT INTO articles (outlet_id, url, published_at, headline)"
            " VALUES ('outlet-b', :url, :published_at, 'Headline')"
        ),
        {"url": "https://a.example/news/1", "published_at": PUBLISHED_AT},
    )
