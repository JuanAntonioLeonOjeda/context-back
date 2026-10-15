"""One `FeedSource` that hands each feed to the reader of its kind."""

from typing import assert_never

from datos.news.application.collect_articles import FeedSource
from datos.news.domain.article import FeedItem
from datos.news.domain.outlet import Feed, FeedKind


class FeedSourceByKind:
    def __init__(self, *, rss: FeedSource, sitemap: FeedSource, section: FeedSource) -> None:
        self._rss = rss
        self._sitemap = sitemap
        self._section = section

    def read(self, feed: Feed) -> list[FeedItem]:
        match feed.kind:
            case FeedKind.RSS:
                return self._rss.read(feed)
            case FeedKind.NEWS_SITEMAP:
                return self._sitemap.read(feed)
            case FeedKind.HTML_SECTION:
                return self._section.read(feed)
            case _:
                assert_never(feed.kind)
