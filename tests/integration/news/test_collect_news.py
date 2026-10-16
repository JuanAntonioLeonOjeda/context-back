from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from datos.http import SourceUnavailableError, build_client
from datos.news.application.collect_articles import Sources, collect_articles
from datos.news.domain.outlet import Feed, FeedKind
from datos.news.domain.tag import clean_tags
from datos.news.infrastructure.article_page_source import ArticlePageSource
from datos.news.infrastructure.csv_source import read_outlets
from datos.news.infrastructure.feed_source_by_kind import FeedSourceByKind
from datos.news.infrastructure.pg_repository import PgNewsRepository
from datos.news.infrastructure.rss_feed_source import RssFeedSource
from datos.news.infrastructure.section_page_source import SectionPageSource
from datos.news.infrastructure.sitemap_feed_source import SitemapFeedSource
from datos.territories.csv_source import read_territories
from datos.territories.repository import PgTerritoryRepository

pytestmark = pytest.mark.integration

DATA = Path("data/news")
FIXTURES = Path("tests/fixtures/feeds")
SITEMAPS = Path("tests/fixtures/sitemaps")
PAGES = Path("tests/fixtures/pages")


def _serve(by_host: dict[str, bytes], pages: list[str] | None = None) -> Sources:
    """Feeds by host. With `pages`, every non-XML URL is an article page, and is recorded."""

    def handler(request: httpx.Request) -> httpx.Response:
        if pages is not None and not request.url.path.endswith(".xml"):
            pages.append(str(request.url))
            return httpx.Response(200, content=(PAGES / "rtvc.html").read_bytes())
        body = by_host.get(request.url.host)
        return httpx.Response(200, content=body) if body else httpx.Response(404)

    client = build_client(httpx.MockTransport(handler))
    readers = FeedSourceByKind(
        rss=RssFeedSource(client),
        sitemap=SitemapFeedSource(client),
        section=SectionPageSource(client),
    )
    return Sources(
        readers, ArticlePageSource(client, delay_s=0), unavailable=(SourceUnavailableError,)
    )


@pytest.fixture(scope="session")
def news_database_url(postgres_url: str) -> str:
    """A database of its own: the collector commits one transaction per feed, so it cannot
    use the rolled-back connection of the other tests without leaking data into them."""
    url = make_url(postgres_url).set(database="news_it")
    admin = create_engine(postgres_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text("CREATE DATABASE news_it"))
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url.render_as_string(hide_password=False))
    command.upgrade(config, "head")
    with create_engine(url).begin() as connection:
        PgTerritoryRepository(connection).upsert_all(
            read_territories(Path("data/territories/territories.csv"))
        )
    return url.render_as_string(hide_password=False)


@pytest.fixture
def engine_url(news_database_url: str) -> str:
    """The news tables are emptied before each test."""
    with create_engine(news_database_url).begin() as connection:
        connection.execute(text("DELETE FROM article_tags"))
        connection.execute(text("DELETE FROM tags"))
        connection.execute(text("DELETE FROM articles"))
        connection.execute(text("DELETE FROM outlets"))
    return news_database_url


def _counts(url: str) -> tuple[int, int]:
    with create_engine(url).connect() as connection:
        outlets = connection.execute(text("SELECT count(*) FROM outlets")).scalar_one()
        articles = connection.execute(text("SELECT count(*) FROM articles")).scalar_one()
    return int(outlets), int(articles)


def test_collects_real_shaped_feeds_and_a_second_run_stores_nothing_new(engine_url: str) -> None:
    outlets = read_outlets(DATA / "outlets.csv")
    feeds = [
        Feed("el-espanol", FeedKind.RSS, "https://www.elespanol.com/rss/espana/", "spain", False),
        Feed(
            "canarias7", FeedKind.RSS, "https://www.canarias7.es/rss/2.0/?section=", "home", False
        ),
        Feed("el-pais", FeedKind.RSS, "https://feeds.elpais.com/rss", "spain", False),
    ]
    source = _serve(
        {
            "www.elespanol.com": (FIXTURES / "el-espanol.xml").read_bytes(),
            "www.canarias7.es": (FIXTURES / "canarias7.xml").read_bytes(),
            "feeds.elpais.com": (FIXTURES / "el-pais.xml").read_bytes(),
        }
    )
    repository = PgNewsRepository(create_engine(engine_url))

    first = collect_articles(feeds, outlets, source, repository)
    second = collect_articles(feeds, outlets, source, repository)

    assert [r.inserted for r in first] == [3, 3, 3]
    assert [r.inserted for r in second] == [0, 0, 0]
    assert _counts(engine_url) == (14, 9)


def test_outlets_keep_the_external_llm_flag_and_default_to_not_allowed(engine_url: str) -> None:
    repository = PgNewsRepository(create_engine(engine_url))
    repository.upsert_outlets(read_outlets(DATA / "outlets.csv"))

    with create_engine(engine_url).connect() as connection:
        rows = connection.execute(text("SELECT id, external_llm_allowed FROM outlets")).all()
        flags: dict[str, bool] = {row[0]: row[1] for row in rows}
        default = connection.execute(
            text(
                "SELECT column_default FROM information_schema.columns"
                " WHERE table_name = 'outlets' AND column_name = 'external_llm_allowed'"
            )
        ).scalar_one()

    assert flags["canarias7"] is False and flags["telemadrid"] is True
    assert default == "false"


def test_a_feed_that_fails_does_not_stop_the_others(engine_url: str) -> None:
    outlets = read_outlets(DATA / "outlets.csv")
    feeds = [
        Feed("abc", FeedKind.RSS, "https://down.example/rss", "home", False),
        Feed(
            "canarias7", FeedKind.RSS, "https://www.canarias7.es/rss/2.0/?section=", "home", False
        ),
    ]
    source = _serve({"www.canarias7.es": (FIXTURES / "canarias7.xml").read_bytes()})

    bad, ok = collect_articles(feeds, outlets, source, PgNewsRepository(create_engine(engine_url)))

    assert bad.error is not None and "HTTPStatusError" in bad.error
    assert ok.inserted == 3


def test_stored_articles_are_metadata_only_and_within_the_limits(engine_url: str) -> None:
    outlets = read_outlets(DATA / "outlets.csv")
    feeds = [Feed("el-espanol", FeedKind.RSS, "https://www.elespanol.com/rss/", "home", False)]
    source = _serve({"www.elespanol.com": (FIXTURES / "el-espanol.xml").read_bytes()})
    collect_articles(feeds, outlets, source, PgNewsRepository(create_engine(engine_url)))

    with create_engine(engine_url).connect() as connection:
        rows = connection.execute(text("SELECT url, headline, lead FROM articles")).all()

    assert rows
    for url, headline, lead in rows:
        assert url.startswith("https://") and "utm_" not in url
        assert headline == headline.strip() and "<" not in headline
        assert lead is None or (len(lead) <= 501 and "<" not in lead)


def test_a_news_sitemap_reads_each_new_page_once_across_runs(engine_url: str) -> None:
    outlets = read_outlets(DATA / "outlets.csv")
    feeds = [Feed("rtvc", FeedKind.NEWS_SITEMAP, "https://rtvc.es/sitemap-news.xml", "all", True)]
    pages: list[str] = []
    sources = _serve({"rtvc.es": (SITEMAPS / "rtvc.xml").read_bytes()}, pages)
    repository = PgNewsRepository(create_engine(engine_url))

    [first] = collect_articles(feeds, outlets, sources, repository)
    [second] = collect_articles(feeds, outlets, sources, repository)

    assert (first.pages_read, first.inserted) == (3, 3)
    assert (second.pages_read, second.inserted) == (0, 0)
    assert len(pages) == 3
    with create_engine(engine_url).connect() as connection:
        leads = connection.execute(text("SELECT lead FROM articles")).scalars().all()
    assert all(leads)


def test_known_urls_returns_only_the_stored_ones_of_that_outlet(engine_url: str) -> None:
    outlets = read_outlets(DATA / "outlets.csv")
    feeds = [Feed("rtvc", FeedKind.NEWS_SITEMAP, "https://rtvc.es/sitemap-news.xml", "all", True)]
    repository = PgNewsRepository(create_engine(engine_url))
    collect_articles(
        feeds, outlets, _serve({"rtvc.es": (SITEMAPS / "rtvc.xml").read_bytes()}, []), repository
    )
    with create_engine(engine_url).connect() as connection:
        stored = connection.execute(text("SELECT url FROM articles LIMIT 1")).scalar_one()

    assert repository.known_urls("rtvc", [stored, "https://rtvc.es/new/"]) == {stored}
    assert repository.known_urls("telemadrid", [stored]) == set()
    assert repository.known_urls("rtvc", []) == set()


def test_the_tags_of_a_real_feed_are_stored_once_and_a_second_read_adds_none(
    engine_url: str,
) -> None:
    outlets = read_outlets(DATA / "outlets.csv")
    feeds = [Feed("el-pais", FeedKind.RSS, "https://feeds.elpais.com/rss", "spain", False)]
    source = _serve({"feeds.elpais.com": (FIXTURES / "el-pais.xml").read_bytes()})
    repository = PgNewsRepository(create_engine(engine_url))

    [first] = collect_articles(feeds, outlets, source, repository)
    [second] = collect_articles(feeds, outlets, source, repository)

    assert first.tags_linked > 3 and second.tags_linked == 0
    with create_engine(engine_url).connect() as connection:
        links = connection.execute(text("SELECT count(*) FROM article_tags")).scalar_one()
        tags = connection.execute(text("SELECT count(*) FROM tags")).scalar_one()
    # "España" and "Ceuta" are on several articles: the tag is one row, the links are many.
    assert links == first.tags_linked and tags < links


def test_an_article_stored_without_tags_gets_them_when_its_feed_is_read_again(
    engine_url: str,
) -> None:
    outlets = read_outlets(DATA / "outlets.csv")
    feeds = [Feed("el-pais", FeedKind.RSS, "https://feeds.elpais.com/rss", "spain", False)]
    source = _serve({"feeds.elpais.com": (FIXTURES / "el-pais.xml").read_bytes()})
    repository = PgNewsRepository(create_engine(engine_url))

    collect_articles(feeds, outlets, source, repository)
    with create_engine(engine_url).begin() as connection:
        connection.execute(text("DELETE FROM article_tags"))  # as before tags existed

    [again] = collect_articles(feeds, outlets, source, repository)

    assert again.inserted == 0 and again.tags_linked > 0


def test_the_tags_of_an_article_keep_the_order_of_the_feed(engine_url: str) -> None:
    outlets = read_outlets(DATA / "outlets.csv")
    feeds = [Feed("el-pais", FeedKind.RSS, "https://feeds.elpais.com/rss", "spain", False)]
    source = _serve({"feeds.elpais.com": (FIXTURES / "el-pais.xml").read_bytes()})

    collect_articles(feeds, outlets, source, PgNewsRepository(create_engine(engine_url)))

    query = text(
        "SELECT array_agg(t.label ORDER BY at.position) FROM article_tags at"
        " JOIN tags t ON t.id = at.tag_id GROUP BY at.article_id"
    )
    with create_engine(engine_url).connect() as connection:
        per_article = connection.execute(query).scalars().all()
    # The first article of the El País fixture lists these four first, in this order.
    assert ["España", "Crisis migratoria", "Ceuta", "Marruecos"] in [t[:4] for t in per_article]


def test_a_link_made_before_tags_had_a_place_gets_it_and_one_that_has_it_keeps_it(
    engine_url: str,
) -> None:
    outlets = read_outlets(DATA / "outlets.csv")
    feeds = [Feed("el-pais", FeedKind.RSS, "https://feeds.elpais.com/rss", "spain", False)]
    source = _serve({"feeds.elpais.com": (FIXTURES / "el-pais.xml").read_bytes()})
    repository = PgNewsRepository(create_engine(engine_url))
    [first] = collect_articles(feeds, outlets, source, repository)
    with create_engine(engine_url).begin() as connection:
        connection.execute(text("UPDATE article_tags SET position = NULL"))

    [again] = collect_articles(feeds, outlets, source, repository)
    [third] = collect_articles(feeds, outlets, source, repository)

    assert again.tags_linked == first.tags_linked and third.tags_linked == 0
    with create_engine(engine_url).connect() as connection:
        missing = connection.execute(
            text("SELECT count(*) FROM article_tags WHERE position IS NULL")
        ).scalar_one()
    assert missing == 0


def test_the_untagged_urls_of_an_outlet_are_the_newest_without_tags_since_a_date(
    engine_url: str,
) -> None:
    from datetime import UTC, datetime

    repository = PgNewsRepository(create_engine(engine_url))
    repository.upsert_outlets(read_outlets(DATA / "outlets.csv"))
    with create_engine(engine_url).begin() as connection:
        for outlet, n, fetched in [
            ("rtve", 1, "2026-10-01"),
            ("rtve", 2, "2026-10-10"),
            ("rtve", 3, "2026-10-12"),
            ("rtve", 4, "2026-10-14"),
            ("3cat", 5, "2026-10-14"),
        ]:
            connection.execute(
                text(
                    "INSERT INTO articles (outlet_id, url, published_at, fetched_at, headline)"
                    " VALUES (:o, :u, :at, :at, 'H')"
                ),
                {"o": outlet, "u": f"https://x.example/{n}", "at": f"{fetched}T10:00:00+00:00"},
            )
    repository.add_tags("rtve", {"https://x.example/4": clean_tags(["Política"])})
    since = datetime(2026, 10, 5, tzinfo=UTC)

    assert repository.untagged_urls("rtve", since=since, limit=10) == [
        "https://x.example/3",
        "https://x.example/2",
    ]
    assert repository.untagged_urls("rtve", since=since, limit=1) == ["https://x.example/3"]
    assert repository.untagged_urls("3cat", since=since, limit=10) == ["https://x.example/5"]
