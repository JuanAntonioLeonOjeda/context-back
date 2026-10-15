"""The bootstrap interval: reproducible, honest about undefined resamples, paired when comparing."""

from collections.abc import Callable, Sequence

import pytest

from datos.classification.domain.bootstrap import _percentile, bootstrap_interval


def share_of(values: Sequence[int]) -> Callable[[Sequence[int]], float]:
    def statistic(positions: Sequence[int]) -> float:
        return sum(values[p] for p in positions) / len(positions)

    return statistic


def test_the_same_seed_gives_the_same_interval() -> None:
    hits = [1] * 140 + [0] * 60

    assert bootstrap_interval(200, share_of(hits), seed=1) == bootstrap_interval(
        200, share_of(hits), seed=1
    )


def test_enough_resamples_that_another_seed_barely_moves_it() -> None:
    # With 2,000 resamples the bounds are stable: a different seed moves them by less than a
    # point. A share of 200 articles moves in steps of 0.005, so they often do not move at all.
    hits = [1] * 140 + [0] * 60
    first = bootstrap_interval(200, share_of(hits), seed=1)
    second = bootstrap_interval(200, share_of(hits), seed=2)

    assert first is not None and second is not None
    assert abs(first.low - second.low) < 0.01
    assert abs(first.high - second.high) < 0.01


def test_few_resamples_depend_on_the_seed() -> None:
    values = [i % 7 for i in range(200)]

    first = bootstrap_interval(200, share_of(values), seed=1, resamples=30)
    second = bootstrap_interval(200, share_of(values), seed=2, resamples=30)

    assert first != second


def test_the_interval_holds_the_point_estimate_and_has_the_width_expected() -> None:
    # 70 % right on 200 articles: the normal approximation gives ±1.96·√(0.7·0.3/200) ≈ ±0.064.
    hits = [1] * 140 + [0] * 60

    interval = bootstrap_interval(200, share_of(hits), seed=7)

    assert interval is not None
    assert interval.low < 0.70 < interval.high
    assert interval.high - interval.low == pytest.approx(0.127, abs=0.02)


def test_a_statistic_that_never_varies_gives_a_point() -> None:
    interval = bootstrap_interval(50, lambda _: 0.5, seed=1, resamples=100)

    assert interval is not None
    assert (interval.low, interval.high, interval.resamples) == (0.5, 0.5, 100)


def test_undefined_resamples_are_left_out_and_counted() -> None:
    calls = iter(range(1000))

    def defined_one_time_in_two(_: Sequence[int]) -> float | None:
        return None if next(calls) % 2 else 1.0

    interval = bootstrap_interval(10, defined_one_time_in_two, seed=1, resamples=100)

    assert interval is not None
    assert interval.resamples == 50


def test_no_defined_resample_gives_no_interval() -> None:
    assert bootstrap_interval(10, lambda _: None, seed=1, resamples=20) is None


def test_a_paired_difference_is_narrower_than_two_separate_intervals() -> None:
    # Both classifiers are right on the same 120 articles; the model is also right on 20 more.
    rules = [1] * 120 + [0] * 80
    model = [1] * 140 + [0] * 60

    def difference(positions: Sequence[int]) -> float:
        return share_of(model)(positions) - share_of(rules)(positions)

    paired = bootstrap_interval(200, difference, seed=3)
    alone = bootstrap_interval(200, share_of(model), seed=3)

    assert paired is not None and alone is not None
    assert paired.low < 0.10 < paired.high
    assert paired.high - paired.low < alone.high - alone.low


def test_refuses_an_empty_set() -> None:
    with pytest.raises(ValueError, match="no articles"):
        bootstrap_interval(0, lambda _: 1.0, seed=1)


@pytest.mark.parametrize(
    ("q", "expected"),
    [(0.0, 1.0), (1.0, 5.0), (0.5, 3.0), (0.25, 2.0), (0.125, 1.5)],
)
def test_percentile_interpolates_between_neighbours(q: float, expected: float) -> None:
    assert _percentile([1.0, 2.0, 3.0, 4.0, 5.0], q) == pytest.approx(expected)
