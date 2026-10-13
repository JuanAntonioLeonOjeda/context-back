"""Reads RSS and Atom feeds over HTTP.

Feeds are untrusted input: bounded in size, parsed by feedparser, never executed.
"""

from collections.abc import Mapping
from datetime import UTC, datetime
from time import struct_time
from typing import Any

import feedparser
import httpx

from datos.news.domain.article import FeedItem
from datos.news.domain.outlet import Feed, FeedKind

# An honest identification: outlets can see who reads their feeds and contact us.
USER_AGENT = "datos-portfolio/0.1 (+https://github.com/JuanAntonioLeonOjeda/context-back; research)"
MAX_FEED_BYTES = 5_000_000


class FeedUnavailableError(Exception):
    """The feed could not be fetched or is not a feed."""


def build_client(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml"},
        timeout=httpx.Timeout(20.0),
        follow_redirects=True,
        transport=transport,
    )


class RssFeedSource:
    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def read(self, feed: Feed) -> list[FeedItem]:
        if feed.kind is not FeedKind.RSS:
            raise FeedUnavailableError(f"{feed.url}: kind {feed.kind} is not supported yet")
        content = self._download(feed.url)
        parsed: Any = feedparser.parse(content)
        # An HTML page (a block page, a login) parses without error but has no feed version.
        if not parsed.version:
            raise FeedUnavailableError(f"{feed.url}: not a readable feed")
        return [_to_item(entry) for entry in parsed.entries]

    def _download(self, url: str) -> bytes:
        try:
            with self._client.stream("GET", url) as response:
                response.raise_for_status()
                chunks: list[bytes] = []
                size = 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > MAX_FEED_BYTES:
                        raise FeedUnavailableError(
                            f"{url}: feed larger than {MAX_FEED_BYTES} bytes"
                        )
                    chunks.append(chunk)
                return b"".join(chunks)
        except httpx.HTTPError as error:
            raise FeedUnavailableError(f"{url}: {type(error).__name__}") from error


def _to_item(entry: Mapping[str, object]) -> FeedItem:
    return FeedItem(
        title=_text(entry, "title"),
        link=_text(entry, "link"),
        published_at=_utc(entry.get("published_parsed") or entry.get("updated_parsed")),
        summary=_text(entry, "summary"),
    )


def _text(entry: Mapping[str, object], key: str) -> str | None:
    value = entry.get(key)
    return value if isinstance(value, str) else None


def _utc(parsed: object) -> datetime | None:
    # feedparser normalises every date to UTC, whatever the offset in the feed.
    if not isinstance(parsed, struct_time):
        return None
    return datetime(*parsed[:6], tzinfo=UTC)
