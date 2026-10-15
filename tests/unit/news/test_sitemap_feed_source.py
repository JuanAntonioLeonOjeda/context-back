from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from datos.http import SourceUnavailableError, build_client
from datos.news.domain.article import DropReason, to_article
from datos.news.domain.outlet import Feed, FeedKind
from datos.news.infrastructure.sitemap_feed_source import SitemapFeedSource

FIXTURES = Path("tests/fixtures")
FEED = Feed("outlet-a", FeedKind.NEWS_SITEMAP, "https://example.org/sitemap.xml", "all", True)


def _read(body: bytes) -> list[object]:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=body))
    return list(SitemapFeedSource(build_client(transport)).read(FEED))


@pytest.mark.parametrize("name", ["rtvc", "telemadrid"])
def test_every_real_sitemap_gives_three_articles_without_lead(name: str) -> None:
    items = SitemapFeedSource(
        build_client(
            httpx.MockTransport(
                lambda request: httpx.Response(
                    200, content=(FIXTURES / "sitemaps" / f"{name}.xml").read_bytes()
                )
            )
        )
    ).read(FEED)

    articles = [to_article("outlet-a", item) for item in items]

    assert len(items) == 3
    assert all(not isinstance(a, DropReason) and a.lead is None for a in articles)


def test_publication_dates_keep_their_offset() -> None:
    # RTVC writes Canary time (+01:00 in summer); Telemadrid writes peninsular time (+02:00).
    body = (FIXTURES / "sitemaps" / "rtvc.xml").read_bytes()
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=body))

    [first, *_] = SitemapFeedSource(build_client(transport)).read(FEED)

    assert first.published_at == datetime(2026, 10, 13, 14, 21, 12, tzinfo=UTC)


def test_a_feed_that_is_not_a_sitemap_is_unavailable() -> None:
    with pytest.raises(SourceUnavailableError, match="not a sitemap"):
        _read((FIXTURES / "feeds" / "canarias7.xml").read_bytes())


def test_a_page_that_is_not_xml_is_unavailable() -> None:
    with pytest.raises(SourceUnavailableError, match="not well-formed XML"):
        _read(b"<html><body>Acceso denegado<br></body></html>")


def test_an_entity_expansion_attack_is_refused() -> None:
    bomb = (
        b'<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">'
        + b"".join(
            f'<!ENTITY lol{i} "{("&lol" + (str(i - 1) if i > 1 else "") + ";") * 10}">'.encode()
            for i in range(1, 10)
        )
        + b']><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">&lol9;</urlset>'
    )

    with pytest.raises(SourceUnavailableError):
        _read(bomb)
