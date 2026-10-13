from collections.abc import Sequence
from datetime import UTC, datetime

from datos.news.application.collect_articles import collect_articles
from datos.news.domain.article import Article, DropReason, FeedItem
from datos.news.domain.outlet import Feed, FeedKind, Outlet

WHEN = datetime(2026, 10, 13, 14, 0, tzinfo=UTC)
OUTLET = Outlet("outlet-a", "Outlet A", "https://a.example", "national", None, True)


def _feed(url: str = "https://a.example/rss", kind: FeedKind = FeedKind.RSS) -> Feed:
    return Feed("outlet-a", kind, url, "home", False)


def _item(n: int, **overrides: object) -> FeedItem:
    values: dict[str, object] = {
        "title": f"Headline {n}",
        "link": f"https://a.example/news/{n}",
        "published_at": WHEN,
        "summary": "Lead",
    }
    return FeedItem(**(values | overrides))  # type: ignore[arg-type]


class FakeSource:
    def __init__(self, by_url: dict[str, list[FeedItem] | Exception]) -> None:
        self._by_url = by_url

    def read(self, feed: Feed) -> list[FeedItem]:
        result = self._by_url[feed.url]
        if isinstance(result, Exception):
            raise result
        return result


class FakeRepository:
    def __init__(self) -> None:
        self.outlets: list[Outlet] = []
        self.stored: dict[tuple[str, str], Article] = {}

    def upsert_outlets(self, outlets: Sequence[Outlet]) -> None:
        self.outlets = list(outlets)

    def add_new(self, articles: Sequence[Article]) -> int:
        new = [a for a in articles if (a.outlet_id, a.url) not in self.stored]
        self.stored.update({(a.outlet_id, a.url): a for a in new})
        return len(new)


class Unavailable(Exception):
    pass


def test_stores_valid_items_and_counts_the_dropped_ones() -> None:
    items = [_item(1), _item(2), _item(3, published_at=None), _item(4, link=None)]
    repository = FakeRepository()

    [result] = collect_articles(
        [_feed()], [OUTLET], FakeSource({"https://a.example/rss": items}), repository
    )

    assert (result.read, result.inserted) == (4, 2)
    assert result.dropped == {DropReason.NO_DATE: 1, DropReason.NO_LINK: 1}


def test_the_outlets_are_stored_before_their_articles() -> None:
    repository = FakeRepository()

    collect_articles([_feed()], [OUTLET], FakeSource({"https://a.example/rss": []}), repository)

    assert repository.outlets == [OUTLET]


def test_reading_the_same_feed_twice_stores_nothing_new() -> None:
    source = FakeSource({"https://a.example/rss": [_item(1), _item(2)]})
    repository = FakeRepository()

    first = collect_articles([_feed()], [OUTLET], source, repository)
    second = collect_articles([_feed()], [OUTLET], source, repository)

    assert (first[0].inserted, second[0].inserted) == (2, 0)


def test_the_same_url_twice_in_one_feed_is_one_article() -> None:
    items = [_item(1), _item(1, title="Updated headline")]

    [result] = collect_articles(
        [_feed()], [OUTLET], FakeSource({"https://a.example/rss": items}), FakeRepository()
    )

    assert result.inserted == 1


def test_the_same_story_with_tracking_parameters_is_one_article() -> None:
    items = [_item(1), _item(1, link="https://a.example/news/1?utm_source=newsletter")]

    [result] = collect_articles(
        [_feed()], [OUTLET], FakeSource({"https://a.example/rss": items}), FakeRepository()
    )

    assert result.inserted == 1


def test_a_failing_feed_does_not_stop_the_others() -> None:
    source = FakeSource(
        {
            "https://a.example/bad": Unavailable("HTTPStatusError"),
            "https://a.example/ok": [_item(1)],
        }
    )

    bad, ok = collect_articles(
        [_feed("https://a.example/bad"), _feed("https://a.example/ok")],
        [OUTLET],
        source,
        FakeRepository(),
        unavailable=(Unavailable,),
    )

    assert bad.error == "HTTPStatusError" and bad.inserted == 0 and not bad.skipped
    assert ok.error is None and ok.inserted == 1


def test_feeds_that_are_not_rss_are_reported_not_collected() -> None:
    [result] = collect_articles(
        [_feed(kind=FeedKind.NEWS_SITEMAP)], [OUTLET], FakeSource({}), FakeRepository()
    )

    assert result.error == "kind news_sitemap not supported yet"
    assert result.skipped is True
