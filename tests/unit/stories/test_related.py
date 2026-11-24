"""The related news: which earlier item is the next step, and how the chain is shown."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from datos.stories.domain.related import (
    Candidate,
    ChainLink,
    NewsItem,
    RelatedSettings,
    fits,
    group_by_day,
    pick_next,
)

SETTINGS = RelatedSettings()
SPAIN = ZoneInfo("Europe/Madrid")


def _item(
    number: int, outlet: str = "abc", *, at: datetime | None = None, headline: str = ""
) -> NewsItem:
    return NewsItem(
        number,
        outlet,
        headline or f"Headline {number}",
        at or datetime(2026, 11, 16, 12, tzinfo=UTC),
    )


def _candidate(item: NewsItem, similarity: float, to_origin: float = 0.9) -> Candidate:
    return Candidate(item, similarity, to_origin)


ORIGIN = ChainLink(
    _item(1, "el-mundo", headline="El juez ordena a Google conservar los datos"), None
)


def test_the_most_similar_candidate_is_the_next_step_whatever_the_order_given() -> None:
    weaker, stronger = _candidate(_item(2), 0.80), _candidate(_item(3), 0.90)

    assert pick_next([weaker, stronger], [ORIGIN], SETTINGS) == stronger


def test_a_candidate_at_the_step_threshold_is_in_and_just_below_is_out() -> None:
    at_threshold = _candidate(_item(2), 0.70)

    assert pick_next([at_threshold], [ORIGIN], SETTINGS) == at_threshold
    assert pick_next([_candidate(_item(2), 0.6999)], [ORIGIN], SETTINGS) is None


def test_a_candidate_far_from_the_news_asked_for_is_skipped_for_the_next_one() -> None:
    # The drift of the Corvillo example: close to the last step, far from where the chain began.
    drifting = _candidate(_item(2), 0.85, to_origin=0.60)
    on_topic = _candidate(_item(3), 0.75, to_origin=0.70)

    assert pick_next([drifting, on_topic], [ORIGIN], SETTINGS) == on_topic


def test_the_origin_threshold_is_inclusive() -> None:
    at_threshold = _candidate(_item(2), 0.80, to_origin=0.65)

    assert pick_next([at_threshold], [ORIGIN], SETTINGS) == at_threshold
    assert pick_next([_candidate(_item(2), 0.80, to_origin=0.6499)], [ORIGIN], SETTINGS) is None


def test_the_same_outlet_publishing_the_same_news_again_is_not_a_step() -> None:
    # The RTVC example: the same item twice, similarity 1.00.
    republished = _candidate(_item(2, "el-mundo"), 1.0)
    other_outlet = _candidate(_item(3, "la-razon"), 0.88)

    assert pick_next([republished, other_outlet], [ORIGIN], SETTINGS) == other_outlet


def test_the_same_headline_of_the_same_outlet_anywhere_in_the_chain_is_a_duplicate() -> None:
    chain = [ORIGIN, ChainLink(_item(2, "abc", headline="Quién es Corvillo"), 0.8)]
    again = _candidate(_item(3, "abc", headline="Quién es Corvillo"), 0.75)

    assert pick_next([again], chain, SETTINGS) is None


def test_a_very_similar_item_of_another_outlet_is_coverage_not_a_duplicate() -> None:
    other_outlet = _candidate(_item(2, "la-razon"), 0.99)

    assert pick_next([other_outlet], [ORIGIN], SETTINGS) == other_outlet


def test_the_same_outlet_just_below_the_duplicate_threshold_is_a_step() -> None:
    same_outlet = _candidate(_item(2, "el-mundo", headline="Otra noticia"), 0.9799)

    assert pick_next([same_outlet], [ORIGIN], SETTINGS) == same_outlet
    assert (
        pick_next([_candidate(_item(2, "el-mundo", headline="Otra"), 0.98)], [ORIGIN], SETTINGS)
        is None
    )


def test_no_candidates_means_the_chain_ends() -> None:
    assert pick_next([], [ORIGIN], SETTINGS) is None


def _on(day: int, hour: int = 12) -> datetime:
    return datetime(2026, 11, day, hour, tzinfo=UTC)


def test_a_candidate_that_would_make_a_ninth_day_does_not_fit() -> None:
    chain = [ChainLink(_item(n, at=_on(17 - n)), 0.8) for n in range(8)]  # 17 to 10 November

    assert fits(chain, _candidate(_item(9, at=_on(10, 8)), 0.8), SETTINGS, SPAIN)  # a day it has
    assert not fits(chain, _candidate(_item(9, at=_on(9)), 0.8), SETTINGS, SPAIN)


def test_the_chain_is_shown_one_day_at_a_time_newest_first() -> None:
    chain = [
        ChainLink(_item(1, at=_on(12, 16)), None),
        ChainLink(_item(2, at=_on(12, 10)), 0.9),
        ChainLink(_item(3, at=_on(5, 13)), 0.85),
    ]

    days = group_by_day(chain, SPAIN)

    assert [(d.day, [link.item.article_id for link in d.links]) for d in days] == [
        (date(2026, 11, 12), [1, 2]),
        (date(2026, 11, 5), [3]),
    ]


def test_a_day_is_the_day_in_spain_not_in_utc() -> None:
    # 23:30 UTC on the 11th is 00:30 on the 12th in Madrid.
    chain = [ChainLink(_item(1, at=_on(12, 10)), None), ChainLink(_item(2, at=_on(11, 23)), 0.9)]
    late = ChainLink(_item(3, at=datetime(2026, 11, 11, 23, 30, tzinfo=UTC)), 0.8)

    days = group_by_day([*chain, late], SPAIN)

    assert [d.day for d in days] == [date(2026, 11, 12)]


def test_the_same_headline_in_another_outlet_is_coverage_not_a_duplicate() -> None:
    # An agency story published word for word by two outlets: two outlets covered it.
    chain = [ORIGIN, ChainLink(_item(2, "abc", headline="Quién es Corvillo"), 0.8)]
    agency_copy = _candidate(_item(3, "la-razon", headline="Quién es Corvillo"), 0.75)

    assert pick_next([agency_copy], chain, SETTINGS) == agency_copy


def test_the_days_come_newest_first_even_if_the_links_are_given_out_of_order() -> None:
    chain = [ChainLink(_item(1, at=_on(5)), None), ChainLink(_item(2, at=_on(12)), 0.9)]

    assert [d.day for d in group_by_day(chain, SPAIN)] == [date(2026, 11, 12), date(2026, 11, 5)]
