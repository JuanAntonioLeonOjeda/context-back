"""The promotion criteria of ADR-0016, against cases computed by hand."""

import pytest

from datos.classification.domain.promotion import (
    EvaluatedArticle,
    outlets_left_behind,
    overall_gain,
)

LABELS = ("sector:education", "sector:health", "level:state", "level:ccaa")
HEALTH = frozenset({"sector:health"})
NOTHING: frozenset[str] = frozenset()


def article(
    article_id: int,
    *,
    gold: frozenset[str],
    rules: frozenset[str],
    candidate: frozenset[str],
    outlet: str = "outlet-a",
    stratum: str = "random",
) -> EvaluatedArticle:
    return EvaluatedArticle(article_id, outlet, stratum, gold, rules, candidate)


def test_gain_is_the_candidates_macro_f1_minus_the_rules_on_the_random_half() -> None:
    # Health in articles 1-4. Rules find 1-2 (F1 = 2·2/(4+2) = 0.667); the candidate finds 1-4
    # (F1 = 1.0). Education nobody has: left out of the macro. Gain = 0.333.
    articles = [
        article(1, gold=HEALTH, rules=HEALTH, candidate=HEALTH),
        article(2, gold=HEALTH, rules=HEALTH, candidate=HEALTH),
        article(3, gold=HEALTH, rules=NOTHING, candidate=HEALTH),
        article(4, gold=HEALTH, rules=NOTHING, candidate=HEALTH),
    ]

    result = overall_gain(articles, LABELS, "sector", seed=1)

    assert result.rules_macro_f1 == pytest.approx(2 / 3)
    assert result.candidate_macro_f1 == 1.0
    assert result.gain == pytest.approx(1 / 3)
    assert (result.articles, result.passes) == (4, True)


def test_the_enriched_half_does_not_count_for_the_gain() -> None:
    articles = [
        article(1, gold=HEALTH, rules=HEALTH, candidate=HEALTH),
        # The candidate wins only in the enriched half: no gain where it counts.
        article(2, gold=HEALTH, rules=NOTHING, candidate=HEALTH, stratum="enriched"),
    ]

    result = overall_gain(articles, LABELS, "sector", seed=1)

    assert (result.gain, result.articles, result.passes) == (0.0, 1, False)


def test_a_gain_above_five_points_passes_and_one_below_does_not() -> None:
    # Ten health articles; rules get 7 of them, the candidate 8: F1 0.824 vs 0.889, gain 0.065.
    # 20 articles, rules 14 and the candidate 15: F1 0.824 vs 0.857, gain 0.034.
    def case(n: int, rules_hits: int, candidate_hits: int) -> list[EvaluatedArticle]:
        return [
            article(
                i,
                gold=HEALTH,
                rules=HEALTH if i < rules_hits else NOTHING,
                candidate=HEALTH if i < candidate_hits else NOTHING,
            )
            for i in range(n)
        ]

    assert overall_gain(case(10, 7, 8), LABELS, "sector", seed=1).passes is True
    assert overall_gain(case(20, 14, 15), LABELS, "sector", seed=1).passes is False


def test_an_undefined_gain_does_not_pass() -> None:
    # Nobody has a level, and none is predicted: no level F1 to compare.
    articles = [article(1, gold=HEALTH, rules=HEALTH, candidate=HEALTH)]

    result = overall_gain(articles, LABELS, "level", seed=1)

    assert (result.gain, result.passes) == (None, False)


def test_the_gain_comes_with_a_paired_interval() -> None:
    articles = [
        article(i, gold=HEALTH, rules=HEALTH if i % 2 else NOTHING, candidate=HEALTH)
        for i in range(40)
    ]

    result = overall_gain(articles, LABELS, "sector", seed=1)

    assert result.interval is not None
    assert result.interval.low <= (result.gain or 0) <= result.interval.high


def test_each_family_is_judged_on_its_own_labels() -> None:
    # The candidate gets the level right and the sector wrong.
    gold = frozenset({"sector:health", "level:ccaa"})
    articles = [
        article(1, gold=gold, rules=gold, candidate=frozenset({"level:ccaa"})),
    ]

    assert overall_gain(articles, LABELS, "level", seed=1).gain == 0.0
    sector = overall_gain(articles, LABELS, "sector", seed=1)
    assert sector.gain == pytest.approx(-1.0)


def test_outlets_count_articles_exactly_right_in_the_family() -> None:
    gold = frozenset({"sector:health", "level:ccaa"})
    articles = [
        # Right for both: the level is not judged in the sector family.
        article(1, gold=gold, rules=gold, candidate=frozenset({"sector:health"})),
        # Rules miss a sector the candidate gets: the candidate is one better.
        article(2, gold=HEALTH, rules=NOTHING, candidate=HEALTH),
        # A second sector predicted: not exactly right.
        article(3, gold=HEALTH, rules=HEALTH, candidate=HEALTH | {"sector:education"}),
    ]

    [outlet] = outlets_left_behind(articles, "sector").outlets

    assert (outlet.articles, outlet.rules_right, outlet.candidate_right) == (3, 2, 2)


def test_two_articles_worse_in_one_outlet_pass_and_three_do_not() -> None:
    def worse(n: int, outlet: str) -> list[EvaluatedArticle]:
        return [
            article(i, gold=HEALTH, rules=HEALTH, candidate=NOTHING, outlet=outlet)
            for i in range(n)
        ]

    better_elsewhere = [
        article(100 + i, gold=HEALTH, rules=NOTHING, candidate=HEALTH, outlet="outlet-b")
        for i in range(10)
    ]

    assert outlets_left_behind(worse(2, "outlet-a") + better_elsewhere, "sector").passes is True
    result = outlets_left_behind(worse(3, "outlet-a") + better_elsewhere, "sector")
    assert result.passes is False
    assert [(o.outlet_id, o.difference) for o in result.outlets] == [
        ("outlet-a", -3),
        ("outlet-b", 10),
    ]


def test_outlets_count_the_whole_test_set_not_only_the_random_half() -> None:
    articles = [
        article(1, gold=HEALTH, rules=HEALTH, candidate=NOTHING, stratum="enriched")
        for _ in range(3)
    ]

    assert outlets_left_behind(articles, "sector").passes is False


def test_a_family_is_promoted_only_when_both_criteria_hold() -> None:
    from datos.classification.domain.promotion import verdicts

    gold = frozenset({"sector:health", "level:ccaa"})
    # Sectors: the candidate finds health where the rules do not, in two outlets alike.
    # Levels: the candidate loses the level in outlet-a three times.
    articles = [
        article(
            i,
            gold=gold,
            rules=frozenset({"level:ccaa"}),
            candidate=frozenset({"sector:health"}) if i < 3 else gold,
            outlet="outlet-a" if i < 6 else "outlet-b",
        )
        for i in range(12)
    ]

    sector, level = verdicts(articles, LABELS, seed=1)

    assert (sector.family, sector.gain.passes, sector.outlets.passes) == ("sector", True, True)
    assert sector.promoted is True
    assert (level.family, level.outlets.passes, level.promoted) == ("level", False, False)


def test_no_articles_cannot_be_evaluated() -> None:
    from datos.classification.domain.promotion import verdicts

    with pytest.raises(ValueError, match="no articles"):
        verdicts([], LABELS, seed=1)


def test_better_overall_but_an_outlet_left_behind_is_not_promoted() -> None:
    from datos.classification.domain.promotion import verdicts

    # Outlet-b: the candidate finds health in 10 articles the rules miss. Outlet-a: it loses 3.
    articles = [
        article(i, gold=HEALTH, rules=NOTHING, candidate=HEALTH, outlet="outlet-b")
        for i in range(10)
    ] + [
        article(100 + i, gold=HEALTH, rules=HEALTH, candidate=NOTHING, outlet="outlet-a")
        for i in range(3)
    ]

    sector = verdicts(articles, LABELS, seed=1)[0]

    assert (sector.gain.passes, sector.outlets.passes) == (True, False)
    assert sector.promoted is False
