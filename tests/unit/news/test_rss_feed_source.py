from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from datos.http import (
    MAX_DOWNLOAD_BYTES,
    USER_AGENT,
    SourceUnavailableError,
    build_client,
)
from datos.news.domain.article import DropReason, to_article
from datos.news.domain.outlet import Feed, FeedKind
from datos.news.infrastructure.rss_feed_source import RssFeedSource

FIXTURES = Path("tests/fixtures/feeds")
FEED = Feed("outlet-a", FeedKind.RSS, "https://example.org/rss", "home", False)


def _source(
    handler: httpx.MockTransport | None = None, *, body: bytes = b"", status: int = 200
) -> RssFeedSource:
    transport = handler or httpx.MockTransport(lambda request: httpx.Response(status, content=body))
    return RssFeedSource(build_client(transport))


def _fixture(name: str) -> bytes:
    return (FIXTURES / f"{name}.xml").read_bytes()


@pytest.mark.parametrize("name", ["el-espanol", "el-pais", "canarias7", "la-vanguardia"])
def test_every_real_feed_gives_three_valid_articles(name: str) -> None:
    items = _source(body=_fixture(name)).read(FEED)

    articles = [to_article("outlet-a", item) for item in items]

    assert len(items) == 3
    assert all(not isinstance(a, DropReason) for a in articles)


def test_the_categories_of_a_feed_are_its_tags() -> None:
    [first, *_] = _source(body=_fixture("el-pais")).read(FEED)

    assert first.tags[:3] == ("España", "Crisis migratoria", "Ceuta")


def test_a_feed_without_categories_has_no_tags() -> None:
    items = _source(body=_fixture("canarias7")).read(FEED)

    assert [item.tags for item in items] == [(), (), ()]


def test_dates_are_utc_whatever_the_offset_of_the_feed() -> None:
    # La Vanguardia writes "13 Oct 2026 15:07:36 +0200" (no weekday); El País uses GMT.
    [first, *_] = _source(body=_fixture("la-vanguardia")).read(FEED)

    assert first.published_at == datetime(2026, 10, 13, 13, 7, 36, tzinfo=UTC)


def test_html_leads_and_padded_titles_are_cleaned_by_the_domain() -> None:
    [first, *_] = _source(body=_fixture("el-espanol")).read(FEED)

    article = to_article("outlet-a", first)

    assert not isinstance(article, DropReason)
    assert "<" not in (article.lead or "") and "http" not in (article.lead or "")
    assert article.headline == article.headline.strip()


def test_the_request_identifies_the_collector() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers["user-agent"])
        return httpx.Response(200, content=_fixture("canarias7"))

    _source(httpx.MockTransport(handler)).read(FEED)

    assert seen == [USER_AGENT]
    assert "datos-portfolio" in USER_AGENT and "github.com" in USER_AGENT


@pytest.mark.parametrize("status", [403, 404, 500])
def test_an_http_error_makes_the_feed_unavailable(status: int) -> None:
    with pytest.raises(SourceUnavailableError, match="HTTPStatusError"):
        _source(status=status).read(FEED)


def test_a_network_failure_makes_the_feed_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("slow", request=request)

    with pytest.raises(SourceUnavailableError, match="ConnectTimeout"):
        _source(httpx.MockTransport(handler)).read(FEED)


def test_a_page_that_is_not_a_feed_is_unavailable() -> None:
    with pytest.raises(SourceUnavailableError, match="not a readable feed"):
        _source(body=b"<html><body>Acceso denegado</body></html>").read(FEED)


def test_an_oversized_feed_is_refused() -> None:
    with pytest.raises(SourceUnavailableError, match="larger than"):
        _source(body=b"x" * (MAX_DOWNLOAD_BYTES + 1)).read(FEED)
