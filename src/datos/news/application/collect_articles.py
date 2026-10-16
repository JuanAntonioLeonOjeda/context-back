"""Use case: collect the articles of every feed, one feed at a time.

A feed that fails never stops the others, and an invalid item never stops its feed: both
are counted and reported (docs: code-style, "validation at the edges").

Feeds whose listing lacks the lead (news sitemaps, section pages) need one request per
article page. Only pages of articles not stored yet are read, and at most
`max_pages_per_feed` per run: a run never floods an outlet, and the rest waits for the
next run.
"""

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol

import structlog

from datos.news.domain.article import (
    Article,
    DropReason,
    FeedItem,
    complete_with_page,
    normalise_url,
    to_article,
)
from datos.news.domain.outlet import Feed, Outlet
from datos.news.domain.tag import Tag, clean_tags

log = structlog.get_logger(__name__)

MAX_PAGES_PER_FEED = 30


class FeedUnavailable(Exception):
    """Port-level failure: the source could not give the feed (adapters translate to it)."""


class FeedSource(Protocol):
    def read(self, feed: Feed) -> list[FeedItem]:
        """Items of a feed; raises an error the use case treats as 'feed unavailable'."""
        ...


class PageSource(Protocol):
    def read(self, url: str) -> FeedItem:
        """The item an article page describes; raises an 'unavailable' error on failure."""
        ...


class NewsRepository(Protocol):
    def upsert_outlets(self, outlets: Sequence[Outlet]) -> None: ...

    def add_new(self, articles: Sequence[Article]) -> int:
        """Store the articles not seen before (same outlet and URL); return how many were new."""
        ...

    def known_urls(self, outlet_id: str, urls: Sequence[str]) -> set[str]:
        """The subset of `urls` already stored for the outlet."""
        ...

    def add_tags(self, outlet_id: str, tags_by_url: Mapping[str, Sequence[Tag]]) -> int:
        """Link tags to stored articles (new or old); return how many links were new."""
        ...


@dataclass(slots=True)
class FeedResult:
    feed: Feed
    read: int = 0
    dropped: Counter[DropReason] = field(default_factory=Counter)
    pages_read: int = 0
    pages_deferred: int = 0  # new articles over the per-run page limit: next run
    inserted: int = 0
    tags_linked: int = 0
    error: str | None = None


@dataclass(frozen=True, slots=True)
class Sources:
    feeds: FeedSource
    pages: PageSource
    unavailable: tuple[type[Exception], ...] = (FeedUnavailable,)


def collect_articles(
    feeds: Sequence[Feed],
    outlets: Sequence[Outlet],
    sources: Sources,
    repository: NewsRepository,
    *,
    max_pages_per_feed: int = MAX_PAGES_PER_FEED,
) -> list[FeedResult]:
    repository.upsert_outlets(outlets)
    results = [_collect_feed(feed, sources, repository, max_pages_per_feed) for feed in feeds]
    log.info(
        "collection_finished",
        feeds=len(results),
        inserted=sum(r.inserted for r in results),
        pages_read=sum(r.pages_read for r in results),
        failed=sum(1 for r in results if r.error),
    )
    return results


def _collect_feed(
    feed: Feed, sources: Sources, repository: NewsRepository, max_pages: int
) -> FeedResult:
    result = FeedResult(feed)
    try:
        items = sources.feeds.read(feed)
    except sources.unavailable as error:
        result.error = str(error)
        log.warning("feed_unavailable", outlet=feed.outlet_id, url=feed.url, reason=result.error)
        return result
    result.read = len(items)
    listed = items  # before the pages are read: the tags are in the listing, new items or not
    if feed.needs_page_fetch:
        items = _complete_new_items(feed, items, sources, repository, max_pages, result)
    articles: dict[str, Article] = {}
    for item in items:
        article = to_article(feed.outlet_id, item)
        if isinstance(article, DropReason):
            result.dropped[article] += 1
        else:
            articles.setdefault(article.url, article)  # the same URL twice in one feed
    result.inserted = repository.add_new(list(articles.values()))
    # After the articles exist. Every listed item, not only the new ones: it completes the articles
    # stored before tags did, and a link already there is left alone.
    result.tags_linked = repository.add_tags(feed.outlet_id, _tags_by_url([*items, *listed]))
    log.info(
        "feed_collected",
        outlet=feed.outlet_id,
        section=feed.section,
        read=result.read,
        dropped=sum(result.dropped.values()),
        pages_read=result.pages_read,
        pages_deferred=result.pages_deferred,
        inserted=result.inserted,
        tags_linked=result.tags_linked,
    )
    return result


def _tags_by_url(items: Sequence[FeedItem]) -> Mapping[str, tuple[Tag, ...]]:
    """The cleaned tags of the items that have a link and at least one valid tag.

    The first item that has tags for a link wins: a page read for the lead can bring the tags the
    listing lacks (ADR-0019), and the listing's own tags come first when it has them.
    """
    by_url: dict[str, tuple[Tag, ...]] = {}
    for item in items:
        tags = clean_tags(item.tags)
        if tags and _has_link(item):
            by_url.setdefault(normalise_url(item.link or ""), tags)
    return by_url


def _complete_new_items(
    feed: Feed,
    items: Sequence[FeedItem],
    sources: Sources,
    repository: NewsRepository,
    max_pages: int,
    result: FeedResult,
) -> list[FeedItem]:
    """New items completed with their page; known ones are left out, they are stored."""
    without_link = sum(1 for item in items if not _has_link(item))
    if without_link:
        result.dropped[DropReason.NO_LINK] += without_link
    new = _new_items(feed.outlet_id, items, repository)
    completed: list[FeedItem] = []
    for item in new[:max_pages]:
        try:
            page = sources.pages.read(item.link or "")
        except sources.unavailable as error:
            result.dropped[DropReason.PAGE_UNAVAILABLE] += 1
            log.warning("page_unavailable", outlet=feed.outlet_id, reason=str(error))
            continue
        result.pages_read += 1
        completed.append(complete_with_page(item, page))
    result.pages_deferred = max(0, len(new) - max_pages)
    return completed


def _new_items(
    outlet_id: str, items: Sequence[FeedItem], repository: NewsRepository
) -> list[FeedItem]:
    """Items with a link whose normalised URL is not stored yet, in listing order, once each."""
    by_url: dict[str, FeedItem] = {}
    for item in items:
        if item.link and _has_link(item):
            by_url.setdefault(normalise_url(item.link), item)
    known = repository.known_urls(outlet_id, list(by_url))
    return [item for url, item in by_url.items() if url not in known]


def _has_link(item: FeedItem) -> bool:
    return bool(item.link and item.link.strip())
