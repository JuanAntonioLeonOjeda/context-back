"""Reads Google News sitemaps: link, title and publication date of recent articles."""

# The standard library parser is safe here: Expat >= 2.4.1 (Python 3.12+ bundles 2.6+)
# rejects entity-expansion attacks such as billion laughs, and no external entity is
# ever resolved by ElementTree.
import xml.etree.ElementTree as ElementTree
from datetime import datetime

import httpx

from datos.news.domain.article import FeedItem
from datos.news.domain.outlet import Feed
from datos.news.infrastructure.http_client import SourceUnavailableError, download

_SITEMAP = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
_NEWS = "{http://www.google.com/schemas/sitemap-news/0.9}"


class SitemapFeedSource:
    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def read(self, feed: Feed) -> list[FeedItem]:
        content = download(self._client, feed.url, accept="application/xml")
        try:
            root = ElementTree.fromstring(content)  # noqa: S314 - safe with Expat, see above
        except ElementTree.ParseError as error:
            raise SourceUnavailableError(f"{feed.url}: not well-formed XML") from error
        if root.tag != f"{_SITEMAP}urlset":
            raise SourceUnavailableError(f"{feed.url}: not a sitemap")
        return [_to_item(url) for url in root.iter(f"{_SITEMAP}url")]


def _to_item(url: ElementTree.Element) -> FeedItem:
    return FeedItem(
        title=url.findtext(f"{_NEWS}news/{_NEWS}title"),
        link=url.findtext(f"{_SITEMAP}loc"),
        published_at=_datetime(url.findtext(f"{_NEWS}news/{_NEWS}publication_date")),
        summary=None,
    )


def _datetime(value: str | None) -> datetime | None:
    """The W3C date of the sitemap; a date without offset stays naive, and is dropped later."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.strip())
    except ValueError:
        return None
