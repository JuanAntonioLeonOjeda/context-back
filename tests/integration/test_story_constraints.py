"""Embeddings and stories keep one vector per version and one story per article in a run (0010)."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError, IntegrityError

pytestmark = pytest.mark.integration

VECTOR = "[" + ",".join(["0.1"] * 768) + "]"


@pytest.fixture
def article_ids(db: Connection) -> tuple[int, int]:
    db.execute(
        text(
            "INSERT INTO territories (id, ine_code, name, level, parent_id)"
            " VALUES ('es', NULL, 'España', 'state', NULL)"
        )
    )
    for outlet in ("outlet-a", "outlet-b"):
        db.execute(
            text(
                "INSERT INTO outlets (id, name, home_url, scope, region_id)"
                " VALUES (:id, :id, 'https://x.example', 'national', NULL)"
            ),
            {"id": outlet},
        )
    ids = [
        int(
            db.execute(
                text(
                    "INSERT INTO articles (outlet_id, url, published_at, headline)"
                    " VALUES (:outlet, :url, :at, 'Headline') RETURNING id"
                ),
                {
                    "outlet": outlet,
                    "url": f"https://x.example/{outlet}",
                    "at": datetime(2026, 10, 1, tzinfo=UTC),
                },
            ).scalar_one()
        )
        for outlet in ("outlet-a", "outlet-b")
    ]
    return ids[0], ids[1]


def _embedding(db: Connection, article_id: int, version: str = "v1", vector: str = VECTOR) -> None:
    db.execute(
        text(
            "INSERT INTO article_embeddings (article_id, encoder_name, encoder_version, embedding)"
            " VALUES (:article, 'encoder', :version, CAST(:vector AS vector))"
        ),
        {"article": article_id, "version": version, "vector": vector},
    )


def _run(db: Connection) -> int:
    return int(
        db.execute(
            text(
                "INSERT INTO story_runs (encoder_version, threshold, window_days)"
                " VALUES ('v1', 0.8, 3) RETURNING id"
            )
        ).scalar_one()
    )


def _story(db: Connection, run_id: int) -> int:
    return int(
        db.execute(
            text("INSERT INTO stories (run_id) VALUES (:run) RETURNING id"), {"run": run_id}
        ).scalar_one()
    )


def _link(db: Connection, run_id: int, story_id: int, article_id: int) -> None:
    db.execute(
        text(
            "INSERT INTO story_articles (run_id, story_id, article_id, similarity)"
            " VALUES (:run, :story, :article, 0.9)"
        ),
        {"run": run_id, "story": story_id, "article": article_id},
    )


def test_an_article_has_one_vector_per_encoder_version(
    db: Connection, article_ids: tuple[int, int]
) -> None:
    _embedding(db, article_ids[0], version="v1")
    _embedding(db, article_ids[0], version="v2")

    with pytest.raises(IntegrityError):
        _embedding(db, article_ids[0], version="v1")


def test_a_vector_of_another_size_is_rejected(db: Connection, article_ids: tuple[int, int]) -> None:
    with pytest.raises(DBAPIError):
        _embedding(db, article_ids[0], vector="[0.1,0.2]")


def test_an_article_is_in_one_story_per_run_but_can_be_in_other_runs(
    db: Connection, article_ids: tuple[int, int]
) -> None:
    first_run, second_run = _run(db), _run(db)
    story = _story(db, first_run)
    _link(db, first_run, story, article_ids[0])

    _link(db, second_run, _story(db, second_run), article_ids[0])
    with pytest.raises(IntegrityError):
        _link(db, first_run, _story(db, first_run), article_ids[0])


def test_a_story_cannot_hold_articles_under_another_run(
    db: Connection, article_ids: tuple[int, int]
) -> None:
    first_run, second_run = _run(db), _run(db)
    story = _story(db, first_run)

    with pytest.raises(IntegrityError):
        _link(db, second_run, story, article_ids[0])


def test_a_run_needs_a_threshold_in_range_and_a_positive_window(db: Connection) -> None:
    with pytest.raises(IntegrityError):
        db.execute(
            text(
                "INSERT INTO story_runs (encoder_version, threshold, window_days)"
                " VALUES ('v1', 1.5, 3)"
            )
        )
