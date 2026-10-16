"""Reads RSS and Atom feeds."""

from collections.abc import Mapping
from datetime import UTC, datetime
from time import struct_time
from typing import Any

import feedparser
import httpx

from datos.http import SourceUnavailableError, download
from datos.news.domain.article import FeedItem
from datos.news.domain.outlet import Feed

_ACCEPT = "application/rss+xml, application/atom+xml, application/xml"


class RssFeedSource:
    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def read(self, feed: Feed) -> list[FeedItem]:
        # feedparser is untyped: Any stops here, and entries become typed FeedItems in _to_item.
        parsed: Any = feedparser.parse(download(self._client, feed.url, accept=_ACCEPT))
        # An HTML page (a block page, a login) parses without error but has no feed version.
        if not parsed.version:
            raise SourceUnavailableError(f"{feed.url}: not a readable feed")
        return [_to_item(entry) for entry in parsed.entries]


def _to_item(entry: Mapping[str, object]) -> FeedItem:
    return FeedItem(
        title=_text(entry, "title"),
        link=_text(entry, "link"),
        published_at=_utc(entry.get("published_parsed") or entry.get("updated_parsed")),
        summary=_text(entry, "summary"),
        tags=_tags(entry),
    )


def _tags(entry: Mapping[str, object]) -> tuple[str, ...]:
    # feedparser puts <category> and <media:keywords> together in `tags`, each as {"term": ...}.
    tags = entry.get("tags")
    if not isinstance(tags, list):
        return ()
    terms = (tag.get("term") for tag in tags if isinstance(tag, Mapping))
    return tuple(term for term in terms if isinstance(term, str))


def _text(entry: Mapping[str, object], key: str) -> str | None:
    value = entry.get(key)
    return value if isinstance(value, str) else None


def _utc(parsed: object) -> datetime | None:
    # feedparser normalises every date to UTC, whatever the offset in the feed.
    if not isinstance(parsed, struct_time):
        return None
    return datetime(*parsed[:6], tzinfo=UTC)
