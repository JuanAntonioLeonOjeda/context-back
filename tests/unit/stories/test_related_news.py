"""Building the chain of related news step by step, with a reader that answers fixed candidates."""

from datetime import UTC, date, datetime

from datos.stories.application.related_news import related_news
from datos.stories.domain.related import Candidate, NewsItem, RelatedSettings


def _on(day: int, hour: int = 12) -> datetime:
    return datetime(2026, 11, day, hour, tzinfo=UTC)


def _item(number: int, day: int, outlet: str = "abc") -> NewsItem:
    return NewsItem(number, outlet, f"Headline {number}", _on(day))


class _Reader:
    """Article 1 on the 16th; each step's candidates are fixed by the test."""

    def __init__(self, candidates: dict[int, list[Candidate]]) -> None:
        self._candidates = candidates
        self.asked: list[tuple[int, int]] = []

    def news_item(self, article_id: int) -> NewsItem | None:
        return _item(1, 16) if article_id == 1 else None

    def candidates(
        self, step_id: int, origin_id: int, settings: RelatedSettings, *, limit: int = 50
    ) -> list[Candidate]:
        self.asked.append((step_id, origin_id))
        return self._candidates.get(step_id, [])


def test_each_step_asks_for_the_candidates_of_the_last_item_against_the_first() -> None:
    reader = _Reader(
        {
            1: [Candidate(_item(2, 12), 0.85, 0.85)],
            2: [Candidate(_item(3, 5), 0.80, 0.70)],
        }
    )

    found = related_news(reader, 1)

    assert reader.asked == [(1, 1), (2, 1), (3, 1)]
    assert found is not None and found.has_related
    assert [(d.day, [link.item.article_id for link in d.links]) for d in found.days] == [
        (date(2026, 11, 16), [1]),
        (date(2026, 11, 12), [2]),
        (date(2026, 11, 5), [3]),
    ]
    assert [link.similarity for d in found.days for link in d.links] == [None, 0.85, 0.80]


def test_the_chain_ends_where_no_candidate_qualifies() -> None:
    reader = _Reader({1: [Candidate(_item(2, 12), 0.60, 0.90)]})  # below 0.70

    found = related_news(reader, 1)

    assert found is not None and not found.has_related
    assert [d.day for d in found.days] == [date(2026, 11, 16)]


def test_the_chain_ends_before_a_ninth_day() -> None:
    # One candidate a day back, from the 15th down: the 16th and seven more days fit, the 8th not.
    candidates = {n: [Candidate(_item(n + 1, 16 - n), 0.9, 0.9)] for n in range(1, 10)}

    found = related_news(_Reader(candidates), 1)

    assert found is not None
    assert [d.day.day for d in found.days] == [16, 15, 14, 13, 12, 11, 10, 9]


def test_the_settings_used_come_with_the_answer() -> None:
    settings = RelatedSettings(step_threshold=0.8)

    found = related_news(_Reader({}), 1, settings)

    assert found is not None and found.settings is settings
    assert found.item == _item(1, 16)


def test_an_unknown_article_has_no_related_news() -> None:
    assert related_news(_Reader({}), 999) is None
