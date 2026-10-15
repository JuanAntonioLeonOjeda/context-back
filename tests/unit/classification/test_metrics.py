"""Per-label F1 and macro-F1 per family, against values computed by hand."""

import pytest

from datos.classification.domain.metrics import FamilyScore, family_scores, label_score

LABELS = ("sector:education", "sector:health", "level:state", "level:ccaa")


def sets(*labels: str) -> frozenset[str]:
    return frozenset(labels)


def by_family(scores: tuple[FamilyScore, ...]) -> dict[str, FamilyScore]:
    return {s.family: s for s in scores}


def test_f1_of_one_label_by_hand() -> None:
    # 4 articles. Gold has health in 1, 2, 3; predicted in 2, 3, 4: TP 2, FP 1, FN 1.
    gold = [sets("sector:health"), sets("sector:health"), sets("sector:health"), sets()]
    predicted = [sets(), sets("sector:health"), sets("sector:health"), sets("sector:health")]

    score = label_score("sector:health", gold, predicted)

    assert (score.support, score.predicted) == (3, 3)
    assert score.f1 == pytest.approx(2 * 2 / (2 * 2 + 1 + 1))  # 0.667


def test_f1_balances_precision_and_recall() -> None:
    # Gold has health in 1 article; predicted in 3, that one included: recall 1, precision 1/3.
    gold = [sets("sector:health"), sets(), sets()]
    predicted = [sets("sector:health"), sets("sector:health"), sets("sector:health")]

    assert label_score("sector:health", gold, predicted).f1 == pytest.approx(0.5)


def test_a_label_never_predicted_scores_zero() -> None:
    gold = [sets("level:state"), sets()]
    predicted = [sets(), sets()]

    assert label_score("level:state", gold, predicted).f1 == 0.0


def test_a_label_absent_from_both_is_undefined_and_left_out_of_the_mean() -> None:
    # Nobody has education: the sector family is the F1 of health alone (1.0), not (1.0 + x) / 2.
    gold = [sets("sector:health"), sets()]
    predicted = [sets("sector:health"), sets()]

    sector = by_family(family_scores(gold, predicted, LABELS))["sector"]

    assert [s.f1 for s in sector.labels] == [None, 1.0]
    assert sector.macro_f1 == 1.0


def test_macro_f1_weighs_a_rare_label_as_much_as_a_common_one() -> None:
    # state: right in 3 of 3 (F1 1.0); ccaa: gold in 1 article, never predicted (F1 0.0).
    gold = [sets("level:state"), sets("level:state"), sets("level:state"), sets("level:ccaa")]
    predicted = [sets("level:state"), sets("level:state"), sets("level:state"), sets()]

    level = by_family(family_scores(gold, predicted, LABELS))["level"]

    assert level.macro_f1 == pytest.approx(0.5)  # micro-F1 would give 6/7 = 0.857


def test_families_are_scored_apart_and_in_the_order_of_the_labels() -> None:
    gold = [sets("sector:education", "level:ccaa")]
    predicted = [sets("sector:education", "level:state")]

    scores = family_scores(gold, predicted, LABELS)

    assert [s.family for s in scores] == ["sector", "level"]
    assert [s.macro_f1 for s in scores] == [1.0, 0.0]


def test_a_family_with_no_defined_label_has_no_score() -> None:
    scores = by_family(family_scores([sets()], [sets()], LABELS))

    assert scores["level"].macro_f1 is None


def test_refuses_gold_and_predicted_of_different_lengths() -> None:
    with pytest.raises(ValueError, match="2 gold and 1 predicted"):
        family_scores([sets(), sets()], [sets()], LABELS)
