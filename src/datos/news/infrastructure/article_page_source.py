"""Reads the metadata an article page publishes for link previews (Open Graph).

Only `<head>` metadata is read: title, description and publication date. The body is
never stored (docs/sources-audit.md, section 7).
"""

import time
from collections.abc import Callable
from datetime import datetime
from html.parser import HTMLParser

import httpx

from datos.http import download
from datos.news.domain.article import FeedItem

# One request per second per collector: polite with outlets that never asked for us.
PAGE_DELAY_S = 1.0


class ArticlePageSource:
    def __init__(
        self,
        client: httpx.Client,
        *,
        delay_s: float = PAGE_DELAY_S,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = client
        self._delay_s = delay_s
        self._sleep = sleep

    def read(self, url: str) -> FeedItem:
        self._sleep(self._delay_s)
        markup = download(self._client, url, accept="text/html")
        return page_item(markup.decode("utf-8", errors="replace"), url)


def page_item(markup: str, url: str) -> FeedItem:
    """The item described by the page's Open Graph metadata."""
    meta = _meta_tags(markup)
    return FeedItem(
        title=_without_site_name(meta.get("og:title"), meta.get("og:site_name")),
        link=url,
        published_at=_datetime(meta.get("article:published_time")),
        summary=meta.get("og:description"),
    )


def _without_site_name(title: str | None, site_name: str | None) -> str | None:
    # 3Cat appends " - 3CatInfo" to og:title; the headline is what comes before it.
    if not title or not site_name:
        return title
    for separator in (" - ", " | "):
        suffix = f"{separator}{site_name}"
        if title.endswith(suffix):
            return title.removesuffix(suffix)
    return title


def _datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.strip())
    except ValueError:
        return None


def _meta_tags(markup: str) -> dict[str, str]:
    collector = _MetaCollector()
    collector.feed(markup)
    collector.close()
    return collector.values


class _MetaCollector(HTMLParser):
    """`<meta property|name=... content=...>` pairs; the first value of each key wins."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.values: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "meta":
            return
        attributes = dict(attrs)
        key = attributes.get("property") or attributes.get("name")
        content = attributes.get("content")
        if key and content:
            self.values.setdefault(key.lower(), content.strip())
