import pytest

from datos.classification.domain.labels import NO_LABELS, Labels, Score


@pytest.mark.parametrize("probability", [0.0, 0.5, 1.0])
def test_a_score_is_a_probability_between_zero_and_one(probability: float) -> None:
    assert Score("sector:health", probability).probability == probability


@pytest.mark.parametrize("probability", [-0.01, 1.01, float("nan")])
def test_a_score_outside_zero_and_one_is_refused(probability: float) -> None:
    with pytest.raises(ValueError, match="sector:health"):
        Score("sector:health", probability)


def test_labels_without_scores_are_what_the_rules_give() -> None:
    assert NO_LABELS.scores == ()


def test_labels_with_the_same_scores_are_equal_and_can_be_hashed() -> None:
    a = Labels(
        frozenset(), frozenset({"health"}), frozenset(), scores=(Score("sector:health", 0.8),)
    )
    b = Labels(
        frozenset(), frozenset({"health"}), frozenset(), scores=(Score("sector:health", 0.8),)
    )

    assert a == b
    assert hash(a) == hash(b)
