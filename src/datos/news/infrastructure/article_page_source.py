"""Reads the metadata an article page publishes for link previews (Open Graph).

Only `<head>` metadata is read: title, description, publication date and the outlet's tags
(`article:tag`). The body is never stored (docs/sources-audit.md, section 7).
"""

import time
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from html.parser import HTMLParser

import httpx

from datos.http import download
from datos.news.domain.article import FeedItem
from datos.news.infrastructure.read_policy import ReadPolicy

# One request per second per collector: polite with outlets that never asked for us.
PAGE_DELAY_S = 1.0


class ArticlePageSource:
    def __init__(
        self,
        client: httpx.Client,
        *,
        delay_s: float = PAGE_DELAY_S,
        sleep: Callable[[float], None] = time.sleep,
        policy: ReadPolicy | None = None,
    ) -> None:
        self._client = client
        self._policy = policy
        self._delay_s = delay_s
        self._sleep = sleep

    def read(self, url: str) -> FeedItem:
        self._sleep(self._delay_s)
        markup = download(self._client, url, accept="text/html").decode("utf-8", errors="replace")
        item = page_item(markup, url)
        # The lead is read as before. The tags only where the site allows it (ADR-0019): its
        # robots.txt (checked on every run) and no mining reservation in the page.
        if self._policy is not None and (
            has_mining_reservation(markup) or not self._policy.allows(url)
        ):
            return replace(item, tags=())
        return item


def page_item(markup: str, url: str) -> FeedItem:
    """The item described by the page's Open Graph metadata."""
    meta, tags = _parse(markup)
    return FeedItem(
        title=_without_site_name(meta.get("og:title"), meta.get("og:site_name")),
        link=url,
        published_at=_datetime(meta.get("article:published_time")),
        summary=meta.get("og:description"),
        tags=tags,
    )


def has_mining_reservation(markup: str) -> bool:
    """`<meta name="tdm-reservation" content="1">`: the page reserves text and data mining."""
    meta, _ = _parse(markup)
    return meta.get("tdm-reservation") == "1"


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


def _parse(markup: str) -> tuple[dict[str, str], tuple[str, ...]]:
    collector = _MetaCollector()
    collector.feed(markup)
    collector.close()
    return collector.values, tuple(collector.tags)


class _MetaCollector(HTMLParser):
    """`<meta property|name=... content=...>` pairs; the first value of each key wins.

    `article:tag` is the exception: it repeats, one per tag (RTVE, 3Cat), or lists them separated
    by commas (Telemadrid). Every value is kept, and split on commas. `keywords` and
    `news_keywords` are not read: Telemadrid fills them with search-engine phrases.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.values: dict[str, str] = {}
        self.tags: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "meta":
            return
        attributes = dict(attrs)
        key = attributes.get("property") or attributes.get("name")
        content = attributes.get("content")
        if not key or not content:
            return
        if key.lower() == "article:tag":
            self.tags.extend(part.strip() for part in content.split(",") if part.strip())
        else:
            self.values.setdefault(key.lower(), content.strip())
