from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

import pytest

from datos.news.application.backfill_page_tags import BackfillResult, backfill_page_tags
from datos.news.domain.article import FeedItem
from datos.news.domain.tag import Tag

SINCE = datetime(2026, 9, 16, tzinfo=UTC)
WHEN = datetime(2026, 10, 16, tzinfo=UTC)


class Unavailable(Exception):
    pass


class _Pages:
    def __init__(self, by_url: dict[str, tuple[str, ...] | Exception]) -> None:
        self._by_url = by_url
        self.requested: list[str] = []

    def read(self, url: str) -> FeedItem:
        self.requested.append(url)
        result = self._by_url[url]
        if isinstance(result, Exception):
            raise result
        return FeedItem("T", url, WHEN, "Lead", tags=result)


class _Repository:
    def __init__(self, untagged: dict[str, list[str]]) -> None:
        self._untagged = untagged
        self.asked: list[tuple[str, int]] = []
        self.linked: dict[str, dict[str, set[str]]] = {}

    def untagged_urls(self, outlet_id: str, *, since: datetime, limit: int) -> list[str]:
        assert since == SINCE
        self.asked.append((outlet_id, limit))
        return self._untagged.get(outlet_id, [])[:limit]

    def add_tags(self, outlet_id: str, tags_by_url: Mapping[str, Sequence[Tag]]) -> int:
        self.linked.setdefault(outlet_id, {}).update(
            {url: {t.key for t in tags} for url, tags in tags_by_url.items()}
        )
        return sum(len(tags) for tags in tags_by_url.values())


def _run(
    pages: _Pages, repository: _Repository, outlets: Sequence[str] = ("rtve",), limit: int = 10
) -> list[BackfillResult]:
    return backfill_page_tags(
        outlets,
        since=SINCE,
        limit=limit,
        pages=pages,
        repository=repository,
        unavailable=(Unavailable,),
    )


def test_each_untagged_article_gets_the_tags_of_its_page() -> None:
    pages = _Pages({"u1": ("Política", "PSOE"), "u2": ("Economía",)})
    repository = _Repository({"rtve": ["u1", "u2"]})

    [result] = _run(pages, repository)

    assert repository.linked == {"rtve": {"u1": {"política", "psoe"}, "u2": {"economía"}}}
    assert (result.read, result.tagged, result.without_tags, result.failed) == (2, 2, 0, 0)


def test_a_page_without_tags_is_counted_and_links_nothing() -> None:
    pages = _Pages({"u1": (), "u2": ("   ", "")})
    repository = _Repository({"rtve": ["u1", "u2"]})

    [result] = _run(pages, repository)

    assert repository.linked == {}
    assert (result.read, result.tagged, result.without_tags) == (2, 0, 2)


def test_a_page_that_fails_does_not_stop_the_others() -> None:
    pages = _Pages({"u1": Unavailable("403"), "u2": ("Política",)})
    repository = _Repository({"rtve": ["u1", "u2"]})

    [result] = _run(pages, repository)

    assert repository.linked == {"rtve": {"u2": {"política"}}}
    assert (result.read, result.tagged, result.failed) == (1, 1, 1)


def test_at_most_the_limit_of_each_outlet_is_asked_for_and_read() -> None:
    pages = _Pages({f"u{n}": ("Tag",) for n in range(5)})
    repository = _Repository({"rtve": [f"u{n}" for n in range(5)]})

    _run(pages, repository, limit=3)

    assert repository.asked == [("rtve", 3)]
    assert pages.requested == ["u0", "u1", "u2"]


def test_every_outlet_is_done_on_its_own() -> None:
    pages = _Pages({"a": ("X",), "b": ("Y",)})
    repository = _Repository({"rtve": ["a"], "3cat": ["b"]})

    results = _run(pages, repository, outlets=("rtve", "3cat"))

    assert [r.outlet_id for r in results] == ["rtve", "3cat"]
    assert repository.linked == {"rtve": {"a": {"x"}}, "3cat": {"b": {"y"}}}


@pytest.mark.parametrize("untagged", [{}, {"rtve": []}])
def test_with_nothing_to_tag_no_page_is_requested(untagged: dict[str, list[str]]) -> None:
    pages = _Pages({})

    [result] = _run(pages, _Repository(untagged))

    assert pages.requested == [] and result.read == 0
