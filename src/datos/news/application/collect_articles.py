"""Use case: collect the articles of every feed, one feed at a time.

A feed that fails never stops the others, and an invalid item never stops its feed: both
are counted and reported (docs: code-style, "validation at the edges").
"""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol

import structlog

from datos.news.domain.article import Article, DropReason, FeedItem, to_article
from datos.news.domain.outlet import Feed, FeedKind, Outlet

log = structlog.get_logger(__name__)


class FeedUnavailable(Exception):
    """Port-level failure: the source could not give the feed (adapters translate to it)."""


class FeedSource(Protocol):
    def read(self, feed: Feed) -> list[FeedItem]:
        """Items of a feed; raises an error the use case treats as 'feed unavailable'."""
        ...


class NewsRepository(Protocol):
    def upsert_outlets(self, outlets: Sequence[Outlet]) -> None: ...

    def add_new(self, articles: Sequence[Article]) -> int:
        """Store the articles not seen before (same outlet and URL); return how many were new."""
        ...


@dataclass(slots=True)
class FeedResult:
    feed: Feed
    read: int = 0
    dropped: Counter[DropReason] = field(default_factory=Counter)
    inserted: int = 0
    error: str | None = None
    skipped: bool = False  # a kind of feed not collected yet: not a failure


def collect_articles(
    feeds: Sequence[Feed],
    outlets: Sequence[Outlet],
    source: FeedSource,
    repository: NewsRepository,
    *,
    unavailable: tuple[type[Exception], ...] = (FeedUnavailable,),
) -> list[FeedResult]:
    repository.upsert_outlets(outlets)
    results = [_collect_feed(feed, source, repository, unavailable) for feed in feeds]
    log.info(
        "collection_finished",
        feeds=len(results),
        inserted=sum(r.inserted for r in results),
        skipped=sum(1 for r in results if r.skipped),
        failed=sum(1 for r in results if r.error and not r.skipped),
    )
    return results


def _collect_feed(
    feed: Feed,
    source: FeedSource,
    repository: NewsRepository,
    unavailable: tuple[type[Exception], ...],
) -> FeedResult:
    result = FeedResult(feed)
    if feed.kind is not FeedKind.RSS:
        result.error = f"kind {feed.kind} not supported yet"
        result.skipped = True
        log.info("feed_skipped", outlet=feed.outlet_id, section=feed.section, reason=result.error)
        return result
    try:
        items = source.read(feed)
    except unavailable as error:
        result.error = str(error)
        log.warning("feed_unavailable", outlet=feed.outlet_id, url=feed.url, reason=result.error)
        return result
    result.read = len(items)
    articles: dict[str, Article] = {}
    for item in items:
        article = to_article(feed.outlet_id, item)
        if isinstance(article, DropReason):
            result.dropped[article] += 1
        else:
            articles.setdefault(article.url, article)  # the same URL twice in one feed
    result.inserted = repository.add_new(list(articles.values()))
    log.info(
        "feed_collected",
        outlet=feed.outlet_id,
        section=feed.section,
        read=result.read,
        dropped=sum(result.dropped.values()),
        inserted=result.inserted,
    )
    return result
