from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine, create_engine, text

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
