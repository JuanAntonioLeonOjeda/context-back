"""Tags are stored once and linked to articles with a known origin (migration 0008)."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError

pytestmark = pytest.mark.integration


@pytest.fixture
def article_id(db: Connection) -> int:
    db.execute(
        text(
            "INSERT INTO territories (id, ine_code, name, level, parent_id)"
            " VALUES ('es', NULL, 'España', 'state', NULL)"
        )
    )
    db.execute(
        text(
            "INSERT INTO outlets (id, name, home_url, scope, region_id)"
            " VALUES ('outlet-a', 'Outlet', 'https://a.example', 'national', NULL)"
        )
    )
    return int(
        db.execute(
            text(
                "INSERT INTO articles (outlet_id, url, published_at, headline)"
                " VALUES ('outlet-a', 'https://a.example/1', :at, 'Headline') RETURNING id"
            ),
            {"at": datetime(2026, 10, 1, tzinfo=UTC)},
        ).scalar_one()
    )


def _tag(db: Connection, key: str = "sanidad", label: str = "Sanidad") -> int:
    return int(
        db.execute(
            text("INSERT INTO tags (key, label) VALUES (:key, :label) RETURNING id"),
            {"key": key, "label": label},
        ).scalar_one()
    )


def _rejected(db: Connection, statement: str, params: dict[str, object]) -> str:
    with pytest.raises(DBAPIError) as error, db.begin_nested():
        db.execute(text(statement), params)
    return str(error.value)


def test_a_tag_exists_once_whatever_its_label(db: Connection) -> None:
    _tag(db, "sanidad", "Sanidad")

    message = _rejected(
        db,
        "INSERT INTO tags (key, label) VALUES ('sanidad', 'SANIDAD')",
        {},
    )

    assert "tags_key_unique" in message


@pytest.mark.parametrize("key", ["Sanidad", " sanidad", "listas  de espera", ""])
def test_a_key_is_lower_case_with_single_spaces_and_not_empty(db: Connection, key: str) -> None:
    message = _rejected(db, "INSERT INTO tags (key, label) VALUES (:key, 'x')", {"key": key})

    assert "tags_key_is_normalised" in message or "tags_key_not_blank" in message


def test_a_label_is_not_blank_and_is_short(db: Connection) -> None:
    assert "tags_label_short" in _rejected(
        db, "INSERT INTO tags (key, label) VALUES ('a', '  ')", {}
    )
    assert "tags_label_short" in _rejected(
        db, "INSERT INTO tags (key, label) VALUES ('b', :label)", {"label": "x" * 101}
    )


def test_an_article_carries_a_tag_once_per_origin(db: Connection, article_id: int) -> None:
    tag_id = _tag(db)
    link = "INSERT INTO article_tags (article_id, tag_id, source) VALUES (:a, :t, :s)"
    db.execute(text(link), {"a": article_id, "t": tag_id, "s": "feed"})
    db.execute(text(link), {"a": article_id, "t": tag_id, "s": "body"})

    message = _rejected(db, link, {"a": article_id, "t": tag_id, "s": "feed"})

    assert "article_tags_pkey" in message


def test_the_origin_of_a_tag_is_one_of_the_known(db: Connection, article_id: int) -> None:
    message = _rejected(
        db,
        "INSERT INTO article_tags (article_id, tag_id, source) VALUES (:a, :t, 'guess')",
        {"a": article_id, "t": _tag(db)},
    )

    assert "article_tags_source_known" in message


def test_a_link_needs_an_existing_article_and_tag(db: Connection, article_id: int) -> None:
    link = "INSERT INTO article_tags (article_id, tag_id, source) VALUES (:a, :t, 'feed')"

    assert "foreign key" in _rejected(db, link, {"a": 0, "t": _tag(db)})
    assert "foreign key" in _rejected(db, link, {"a": article_id, "t": 0})
