"""The curve's summary and the rule of D12: mean per size, rise paired by fold, three points."""

from dataclasses import dataclass

import pytest

from datos.classification.domain.learning_curve import RiseVerdict, rise_verdicts, summarise
from datos.classification.domain.metrics import FamilyScore


@dataclass(frozen=True)
class Point:
    fold: int
    size: int
    scores: tuple[FamilyScore, ...]


def point(fold: int, size: int, sector: float | None, level: float | None = 0.5) -> Point:
    return Point(fold, size, (FamilyScore("sector", sector, ()), FamilyScore("level", level, ())))


def verdict(points: list[Point], family: str = "sector") -> RiseVerdict:
    return next(v for v in rise_verdicts(points) if v.family == family)


def test_summary_gives_the_mean_over_folds_per_family_and_size() -> None:
    points = [point(0, 200, 0.6), point(1, 200, 0.7), point(0, 100, 0.4), point(1, 100, 0.5)]

    sector = [s for s in summarise(points) if s.family == "sector"]

    assert [(s.size, s.fold_scores) for s in sector] == [(100, (0.4, 0.5)), (200, (0.6, 0.7))]
    assert [s.mean_macro_f1 for s in sector] == [pytest.approx(0.45), pytest.approx(0.65)]


def test_a_fold_without_a_score_is_left_out_of_the_mean() -> None:
    summary = summarise([point(0, 100, 0.4), point(1, 100, None)])

    assert summary[0].fold_scores == (0.4,)
    assert summary[0].mean_macro_f1 == 0.4


def test_three_points_from_200_to_300_still_rise() -> None:
    points = [point(0, 200, 0.80), point(0, 300, 0.83)]  # 0.83 - 0.80 = 0.0299999… in floats

    assert verdict(points).still_rises is True


def test_less_than_three_points_do_not() -> None:
    points = [point(0, 200, 0.80), point(0, 300, 0.829)]

    assert verdict(points).still_rises is False


def test_the_rise_is_the_mean_of_each_folds_rise() -> None:
    # Fold 0 rises 6 points, fold 1 none: 3 points on average.
    points = [point(0, 200, 0.6), point(0, 300, 0.66), point(1, 200, 0.7), point(1, 300, 0.7)]

    result = verdict(points)

    assert result.rise == pytest.approx(0.03)
    assert (result.folds, result.still_rises) == (2, True)


def test_a_fold_cut_before_300_is_not_compared() -> None:
    # Fold 1 stopped at 200. Unpaired, the means (0.6 + 0.9) / 2 = 0.75 and 0.62 would fall 13
    # points; paired, fold 0 rises 2.
    points = [point(0, 200, 0.6), point(0, 300, 0.62), point(1, 200, 0.9)]

    result = verdict(points)

    assert result.rise == pytest.approx(0.02)
    assert result.folds == 1


def test_no_fold_with_both_sizes_cannot_tell() -> None:
    result = verdict([point(0, 200, 0.6), point(1, 300, 0.7)])

    assert (result.rise, result.folds, result.still_rises) == (None, 0, None)


def test_each_family_has_its_own_verdict() -> None:
    points = [point(0, 200, 0.6, level=0.5), point(0, 300, 0.6, level=0.6)]

    assert verdict(points, "sector").still_rises is False
    assert verdict(points, "level").still_rises is True


def test_label_more_when_either_family_rises() -> None:
    from datos.classification.domain.learning_curve import label_more

    points = [point(0, 200, 0.6, level=0.5), point(0, 300, 0.6, level=0.6)]

    assert label_more(rise_verdicts(points)) is True


def test_no_more_labels_when_no_family_rises() -> None:
    from datos.classification.domain.learning_curve import label_more

    points = [point(0, 200, 0.6, level=0.5), point(0, 300, 0.6, level=0.5)]

    assert label_more(rise_verdicts(points)) is False


def test_a_curve_not_yet_measured_gives_no_answer() -> None:
    from datos.classification.domain.learning_curve import label_more

    assert label_more(rise_verdicts([point(0, 200, 0.6), point(0, 100, 0.5)])) is None


def test_one_family_that_rises_decides_even_if_the_other_cannot_be_told() -> None:
    from datos.classification.domain.learning_curve import label_more

    points = [point(0, 200, 0.6, level=None), point(0, 300, 0.7, level=None)]
    verdicts = rise_verdicts(points)

    assert [v.still_rises for v in verdicts] == [True, None]
    assert label_more(verdicts) is True
