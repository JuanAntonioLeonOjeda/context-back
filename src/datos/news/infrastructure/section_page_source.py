"""Reads an outlet's section page and keeps the links that point to articles.

Which links are articles is configuration, not code: each `html_section` feed carries an
`article_url_pattern` in `data/news/feeds.csv` (for RTVE, a date and an id in the path).
"""

import re
from html.parser import HTMLParser
from urllib.parse import urljoin

import httpx

from datos.news.domain.article import FeedItem
from datos.news.domain.outlet import Feed
from datos.news.infrastructure.http_client import SourceUnavailableError, download


class SectionPageSource:
    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def read(self, feed: Feed) -> list[FeedItem]:
        if not feed.article_url_pattern:
            raise SourceUnavailableError(f"{feed.url}: no article_url_pattern configured")
        markup = download(self._client, feed.url, accept="text/html")
        links = article_links(
            markup.decode("utf-8", errors="replace"), feed.url, feed.article_url_pattern
        )
        # Title, date and lead come later from each article page (needs_page_fetch).
        return [FeedItem(title=None, link=link, published_at=None, summary=None) for link in links]


def article_links(markup: str, base_url: str, pattern: str) -> list[str]:
    """Absolute links of the page that fully match `pattern`, once each, in page order."""
    matcher = re.compile(pattern)
    collector = _LinkCollector()
    collector.feed(markup)
    collector.close()
    absolute = (urljoin(base_url, href) for href in collector.hrefs)
    return list(dict.fromkeys(link for link in absolute if matcher.fullmatch(link)))


class _LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.hrefs.append(href.strip())
