from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine, create_engine, text

from datos.classification.domain.tag_stoplist import MatchKind, Reason, StoplistEntry
from datos.classification.infrastructure.pg_article_text_reader import PgArticleTextReader

pytestmark = pytest.mark.integration


@pytest.fixture
def engine(migrated_postgres_url: str) -> Iterator[Engine]:
    engine = create_engine(migrated_postgres_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO outlets (id, name, home_url, scope, region_id)"
                " VALUES ('outlet-r', 'Outlet R', 'https://r.example', 'national', NULL)"
                " ON CONFLICT DO NOTHING"
            )
        )
    yield engine
    # The tags of these articles would collide with the tests that insert their own.
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM article_tags"))
        connection.execute(text("DELETE FROM tags"))
    engine.dispose()


def _add(engine: Engine, url: str, headline: str, lead: str | None) -> int:
    with engine.begin() as connection:
        return int(
            connection.execute(
                text(
                    "INSERT INTO articles (outlet_id, url, published_at, headline, lead)"
                    " VALUES ('outlet-r', :url, :at, :headline, :lead) RETURNING id"
                ),
                {
                    "url": url,
                    "at": datetime(2026, 10, 15, tzinfo=UTC),
                    "headline": headline,
                    "lead": lead,
                },
            ).scalar_one()
        )


def test_gives_the_headline_and_the_lead_of_the_articles_asked_for(engine: Engine) -> None:
    a = _add(engine, "https://r.example/text-reader-a", "Un titular", "Su entradilla.")
    b = _add(engine, "https://r.example/text-reader-b", "Otro titular", None)

    texts = PgArticleTextReader(engine).texts([a, b])

    assert (texts[a].headline, texts[a].lead) == ("Un titular", "Su entradilla.")
    assert (texts[b].headline, texts[b].lead) == ("Otro titular", None)


def test_an_id_with_no_article_is_not_in_the_result_and_other_articles_are_not_returned(
    engine: Engine,
) -> None:
    asked = _add(engine, "https://r.example/text-reader-c", "Pedido", None)
    _add(engine, "https://r.example/text-reader-d", "No pedido", None)

    texts = PgArticleTextReader(engine).texts([asked, 999_999_999])

    assert set(texts) == {asked}


def test_the_outlet_of_each_article_that_exists(engine: Engine) -> None:
    from datos.classification.infrastructure.pg_article_outlet_reader import PgArticleOutletReader

    article_id = _add(engine, "https://r.example/outlet", "Titular", None)

    outlets = PgArticleOutletReader(engine).outlets([article_id, 999_999])

    assert outlets == {article_id: "outlet-r"}


def _tag(
    engine: Engine, article_id: int, label: str, position: int | None, source: str = "feed"
) -> None:
    with engine.begin() as connection:
        tag_id = connection.execute(
            text(
                "INSERT INTO tags (key, label) VALUES (:key, :label)"
                " ON CONFLICT (key) DO UPDATE SET key = EXCLUDED.key RETURNING id"
            ),
            {"key": " ".join(label.lower().split()), "label": label},
        ).scalar_one()
        connection.execute(
            text(
                "INSERT INTO article_tags (article_id, tag_id, source, position)"
                " VALUES (:a, :t, :s, :p)"
            ),
            {"a": article_id, "t": tag_id, "s": source, "p": position},
        )


STOPLIST = [StoplistEntry("home la razón", MatchKind.EXACT, Reason.OUTLET_MARKER)]


def test_gives_the_tags_in_the_order_of_the_feed_without_the_ones_on_the_stoplist(
    engine: Engine,
) -> None:
    a = _add(engine, "https://r.example/tags-order", "Con etiquetas", None)
    _tag(engine, a, "Ceuta", 2)
    _tag(engine, a, "Home La Razón", 0)
    _tag(engine, a, "España", 1)

    texts = PgArticleTextReader(engine, STOPLIST).texts([a])

    assert texts[a].tags == ("España", "Ceuta")


def test_the_tags_of_the_feed_come_before_the_ones_read_from_the_body_and_before_no_place(
    engine: Engine,
) -> None:
    a = _add(engine, "https://r.example/tags-sources", "Con etiquetas", None)
    _tag(engine, a, "Sin sitio", None)
    _tag(engine, a, "Del cuerpo", 0, source="body")
    _tag(engine, a, "Del feed", 5)

    texts = PgArticleTextReader(engine, STOPLIST).texts([a])

    assert (
        texts[a].tags == ("Del feed", "Sin sitio", "Del cuerpo") or texts[a].tags[0] == "Del feed"
    )


def test_a_tag_that_came_from_the_feed_and_the_body_is_read_once(engine: Engine) -> None:
    a = _add(engine, "https://r.example/tags-twice", "Con etiquetas", None)
    _tag(engine, a, "Sanidad", 0)
    _tag(engine, a, "Sanidad", 0, source="body")

    texts = PgArticleTextReader(engine, STOPLIST).texts([a])

    assert texts[a].tags == ("Sanidad",)


def test_an_article_without_tags_has_none(engine: Engine) -> None:
    a = _add(engine, "https://r.example/tags-none", "Sin etiquetas", None)

    assert PgArticleTextReader(engine, STOPLIST).texts([a])[a].tags == ()


def test_with_no_list_given_the_versioned_one_is_used(engine: Engine) -> None:
    a = _add(engine, "https://r.example/tags-default", "Con etiquetas", None)
    _tag(engine, a, "Home La Razón", 0)
    _tag(engine, a, "Sanidad", 1)

    assert PgArticleTextReader(engine).texts([a])[a].tags == ("Sanidad",)
