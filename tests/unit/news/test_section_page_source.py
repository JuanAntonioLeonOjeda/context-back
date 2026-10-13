from pathlib import Path

import httpx
import pytest

from datos.news.domain.outlet import Feed, FeedKind
from datos.news.infrastructure.http_client import SourceUnavailableError, build_client
from datos.news.infrastructure.section_page_source import SectionPageSource, article_links

SECTIONS = Path("tests/fixtures/sections")
RTVE = r"https://www\.rtve\.es/noticias/\d{8}/[^/?#]+/\d+\.shtml"
CAT = r"https://www\.3cat\.cat/3catinfo/[^/?#]+/noticia/\d+/"


def test_only_links_matching_the_pattern_are_articles_once_each_in_page_order() -> None:
    markup = (SECTIONS / "3cat-politica.html").read_text(encoding="utf-8")

    links = article_links(markup, "https://www.3cat.cat/3catinfo/politica/", CAT)

    # The real page also links skip-links and other 3Cat sites (esport3); the first
    # article appears twice.
    assert len(links) == 3
    assert all(link.startswith("https://www.3cat.cat/3catinfo/") for link in links)
    assert links[0].endswith("/noticia/3433737/")


def test_relative_and_absolute_links_end_up_absolute() -> None:
    markup = '<a href="/noticias/20261013/a-b/1.shtml">x</a><a href="https://www.rtve.es/noticias/20261013/c/2.shtml">y</a>'

    links = article_links(markup, "https://www.rtve.es/noticias/politica/", RTVE)

    assert links == [
        "https://www.rtve.es/noticias/20261013/a-b/1.shtml",
        "https://www.rtve.es/noticias/20261013/c/2.shtml",
    ]


def test_a_real_rtve_section_gives_article_links_without_title_or_date() -> None:
    body = (SECTIONS / "rtve-politica.html").read_bytes()
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=body))
    feed = Feed(
        "rtve",
        FeedKind.HTML_SECTION,
        "https://www.rtve.es/noticias/politica/",
        "politics",
        True,
        RTVE,
    )

    items = SectionPageSource(build_client(transport)).read(feed)

    # The real page links each article more than once (headline, image, live block).
    assert len(items) == 2
    assert all(item.title is None and item.published_at is None for item in items)


def test_a_section_feed_without_pattern_is_unavailable() -> None:
    feed = Feed("rtve", FeedKind.HTML_SECTION, "https://www.rtve.es/x/", "politics", True)
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=b""))

    with pytest.raises(SourceUnavailableError, match="article_url_pattern"):
        SectionPageSource(build_client(transport)).read(feed)
