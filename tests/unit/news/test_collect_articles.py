from collections.abc import Sequence
from datetime import UTC, datetime

from datos.news.application.collect_articles import Sources, collect_articles
from datos.news.domain.article import Article, DropReason, FeedItem
from datos.news.domain.outlet import Feed, FeedKind, Outlet

WHEN = datetime(2026, 10, 13, 14, 0, tzinfo=UTC)
OUTLET = Outlet("outlet-a", "Outlet A", "https://a.example", "national", None, True)


def _feed(
    url: str = "https://a.example/rss",
    kind: FeedKind = FeedKind.RSS,
    *,
    needs_page_fetch: bool = False,
) -> Feed:
    return Feed("outlet-a", kind, url, "home", needs_page_fetch)


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

    def known_urls(self, outlet_id: str, urls: Sequence[str]) -> set[str]:
        return {url for url in urls if (outlet_id, url) in self.stored}


class FakePages:
    """Article pages by URL; records every request so tests can count them."""

    def __init__(self, by_url: dict[str, FeedItem | Exception] | None = None) -> None:
        self._by_url = by_url or {}
        self.requested: list[str] = []

    def read(self, url: str) -> FeedItem:
        self.requested.append(url)
        page = self._by_url.get(url, FeedItem("Page title", url, WHEN, "Page lead"))
        if isinstance(page, Exception):
            raise page
        return page


class Unavailable(Exception):
    pass


def _sources(
    by_url: dict[str, list[FeedItem] | Exception], pages: FakePages | None = None
) -> Sources:
    return Sources(FakeSource(by_url), pages or FakePages(), unavailable=(Unavailable,))


def test_stores_valid_items_and_counts_the_dropped_ones() -> None:
    items = [_item(1), _item(2), _item(3, published_at=None), _item(4, link=None)]
    repository = FakeRepository()

    [result] = collect_articles(
        [_feed()], [OUTLET], _sources({"https://a.example/rss": items}), repository
    )

    assert (result.read, result.inserted) == (4, 2)
    assert result.dropped == {DropReason.NO_DATE: 1, DropReason.NO_LINK: 1}


def test_the_outlets_are_stored_before_their_articles() -> None:
    repository = FakeRepository()

    collect_articles([_feed()], [OUTLET], _sources({"https://a.example/rss": []}), repository)

    assert repository.outlets == [OUTLET]


def test_reading_the_same_feed_twice_stores_nothing_new() -> None:
    source = _sources({"https://a.example/rss": [_item(1), _item(2)]})
    repository = FakeRepository()

    first = collect_articles([_feed()], [OUTLET], source, repository)
    second = collect_articles([_feed()], [OUTLET], source, repository)

    assert (first[0].inserted, second[0].inserted) == (2, 0)


def test_the_same_url_twice_in_one_feed_is_one_article() -> None:
    items = [_item(1), _item(1, title="Updated headline")]

    [result] = collect_articles(
        [_feed()], [OUTLET], _sources({"https://a.example/rss": items}), FakeRepository()
    )

    assert result.inserted == 1


def test_the_same_story_with_tracking_parameters_is_one_article() -> None:
    items = [_item(1), _item(1, link="https://a.example/news/1?utm_source=newsletter")]

    [result] = collect_articles(
        [_feed()], [OUTLET], _sources({"https://a.example/rss": items}), FakeRepository()
    )

    assert result.inserted == 1


def test_a_failing_feed_does_not_stop_the_others() -> None:
    source = _sources(
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
    )

    assert bad.error == "HTTPStatusError" and bad.inserted == 0
    assert ok.error is None and ok.inserted == 1


SITEMAP = "https://a.example/sitemap.xml"


def _listed(n: int) -> FeedItem:
    # A news sitemap: link, title and date, no lead.
    return _item(n, summary=None)


def test_a_listing_without_leads_is_completed_with_each_article_page() -> None:
    repository = FakeRepository()

    [result] = collect_articles(
        [_feed(SITEMAP, FeedKind.NEWS_SITEMAP, needs_page_fetch=True)],
        [OUTLET],
        _sources({SITEMAP: [_listed(1), _listed(2)]}),
        repository,
    )

    assert (result.pages_read, result.inserted) == (2, 2)
    assert {a.lead for a in repository.stored.values()} == {"Page lead"}


def test_what_the_listing_says_wins_over_the_page() -> None:
    repository = FakeRepository()

    collect_articles(
        [_feed(SITEMAP, FeedKind.NEWS_SITEMAP, needs_page_fetch=True)],
        [OUTLET],
        _sources({SITEMAP: [_listed(1)]}),
        repository,
    )

    [article] = repository.stored.values()
    assert article.headline == "Headline 1"


def test_a_section_page_link_takes_title_and_date_from_its_page() -> None:
    link_only = FeedItem(None, "https://a.example/news/1", None, None)
    repository = FakeRepository()

    [result] = collect_articles(
        [_feed(SITEMAP, FeedKind.HTML_SECTION, needs_page_fetch=True)],
        [OUTLET],
        _sources({SITEMAP: [link_only]}),
        repository,
    )

    [article] = repository.stored.values()
    assert result.inserted == 1
    assert (article.headline, article.published_at) == ("Page title", WHEN)


def test_pages_of_stored_articles_are_never_requested_again() -> None:
    pages = FakePages()
    sources = _sources({SITEMAP: [_listed(1), _listed(2)]}, pages)
    feed = _feed(SITEMAP, FeedKind.NEWS_SITEMAP, needs_page_fetch=True)
    repository = FakeRepository()

    collect_articles([feed], [OUTLET], sources, repository)
    [second] = collect_articles([feed], [OUTLET], sources, repository)

    assert len(pages.requested) == 2
    assert (second.pages_read, second.inserted) == (0, 0)


def test_new_pages_over_the_limit_wait_for_the_next_run() -> None:
    pages = FakePages()
    sources = _sources({SITEMAP: [_listed(n) for n in range(5)]}, pages)
    feed = _feed(SITEMAP, FeedKind.NEWS_SITEMAP, needs_page_fetch=True)
    repository = FakeRepository()

    [first] = collect_articles([feed], [OUTLET], sources, repository, max_pages_per_feed=3)
    [second] = collect_articles([feed], [OUTLET], sources, repository, max_pages_per_feed=3)

    assert (first.pages_read, first.pages_deferred, first.inserted) == (3, 2, 3)
    assert (second.pages_read, second.pages_deferred, second.inserted) == (2, 0, 2)


def test_an_unavailable_page_drops_only_its_article() -> None:
    pages = FakePages({"https://a.example/news/1": Unavailable("HTTPStatusError")})

    [result] = collect_articles(
        [_feed(SITEMAP, FeedKind.NEWS_SITEMAP, needs_page_fetch=True)],
        [OUTLET],
        _sources({SITEMAP: [_listed(1), _listed(2)]}, pages),
        FakeRepository(),
    )

    assert result.dropped == {DropReason.PAGE_UNAVAILABLE: 1}
    assert result.inserted == 1 and result.error is None


def test_a_listed_item_without_link_is_counted_not_requested() -> None:
    pages = FakePages()

    [result] = collect_articles(
        [_feed(SITEMAP, FeedKind.NEWS_SITEMAP, needs_page_fetch=True)],
        [OUTLET],
        _sources({SITEMAP: [_listed(1), _item(2, link=None)]}, pages),
        FakeRepository(),
    )

    assert result.dropped == {DropReason.NO_LINK: 1}
    assert pages.requested == ["https://a.example/news/1"]
