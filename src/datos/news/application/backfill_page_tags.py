"""Use case: give their tags to the stored articles that have none, from their own page (ADR-0019).

For the outlets whose feed carries no tags but whose pages do (`tags_in_page` in feeds.csv). The
articles collected before the page was read for tags are in this case. One request per article and
one per second, newest first, at most `limit` per outlet: a run never floods an outlet. An article
whose page has no tags is read again by the next run, so the window (`since`) bounds the work.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import structlog

from datos.news.domain.article import FeedItem
from datos.news.domain.tag import Tag, clean_tags

log = structlog.get_logger(__name__)


class PageSource(Protocol):
    def read(self, url: str) -> FeedItem:
        """The item an article page describes; raises an 'unavailable' error on failure."""
        ...


class UntaggedArticles(Protocol):
    def untagged_urls(self, outlet_id: str, *, since: datetime, limit: int) -> list[str]:
        """URLs of the outlet's articles collected since `since` that have no tag, newest first."""
        ...

    def add_tags(self, outlet_id: str, tags_by_url: Mapping[str, Sequence[Tag]]) -> int:
        """Link tags to stored articles; return how many links were new."""
        ...


@dataclass(slots=True)
class BackfillResult:
    outlet_id: str
    read: int = 0
    tagged: int = 0  # articles that got at least one tag
    without_tags: int = (
        0  # pages read that publish none, or that the site does not allow us to read
    )
    failed: int = 0


def backfill_page_tags(
    outlet_ids: Sequence[str],
    *,
    since: datetime,
    limit: int,
    pages: PageSource,
    repository: UntaggedArticles,
    unavailable: tuple[type[Exception], ...],
) -> list[BackfillResult]:
    results = [
        _backfill_outlet(o, since, limit, pages, repository, unavailable) for o in outlet_ids
    ]
    log.info(
        "page_tags_backfilled",
        outlets=len(results),
        read=sum(r.read for r in results),
        tagged=sum(r.tagged for r in results),
        failed=sum(r.failed for r in results),
    )
    return results


def _backfill_outlet(
    outlet_id: str,
    since: datetime,
    limit: int,
    pages: PageSource,
    repository: UntaggedArticles,
    unavailable: tuple[type[Exception], ...],
) -> BackfillResult:
    result = BackfillResult(outlet_id)
    found: dict[str, tuple[Tag, ...]] = {}
    for url in repository.untagged_urls(outlet_id, since=since, limit=limit):
        try:
            item = pages.read(url)
        except unavailable as error:
            result.failed += 1
            log.warning("page_unavailable", outlet=outlet_id, reason=str(error))
            continue
        result.read += 1
        tags = clean_tags(item.tags)
        if tags:
            found[url] = tags
        else:
            result.without_tags += 1
    if found:
        repository.add_tags(outlet_id, found)
    result.tagged = len(found)
    log.info(
        "page_tags_backfilled_outlet", outlet=outlet_id, read=result.read, tagged=result.tagged
    )
    return result
