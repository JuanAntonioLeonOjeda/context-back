import pytest

from datos.news.domain.article import FeedItem
from datos.news.domain.outlet import Feed, FeedKind
from datos.news.infrastructure.feed_source_by_kind import FeedSourceByKind


class Named:
    def __init__(self, name: str) -> None:
        self._name = name

    def read(self, feed: Feed) -> list[FeedItem]:
        return [FeedItem(self._name, None, None, None)]


@pytest.mark.parametrize(
    ("kind", "reader"),
    [(FeedKind.RSS, "rss"), (FeedKind.NEWS_SITEMAP, "sitemap"), (FeedKind.HTML_SECTION, "section")],
)
def test_each_feed_goes_to_the_reader_of_its_kind(kind: FeedKind, reader: str) -> None:
    source = FeedSourceByKind(rss=Named("rss"), sitemap=Named("sitemap"), section=Named("section"))

    [item] = source.read(Feed("outlet-a", kind, "https://a.example/", "home", False))

    assert item.title == reader
