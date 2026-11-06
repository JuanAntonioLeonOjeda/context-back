"""How much a metric on ~200 articles could move: a bootstrap interval (ADR-0016).

Pure: the number of articles, a statistic over a sample of their positions and a seed in, an
interval out. Each resample draws as many positions as there are articles, with replacement, and
computes the statistic on them. A statistic that compares two classifiers computes both on the same
positions, so the interval is of the paired difference: an article both get wrong does not widen it.

The interval is shown next to each number; it decides nothing. The promotion criteria apply to the
point estimates, as the author decided in ADR-0016.
"""

import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass

RESAMPLES = 2000
LEVEL = 0.95


@dataclass(frozen=True, slots=True)
class Interval:
    low: float
    high: float
    resamples: int  # the resamples where the statistic was defined


def bootstrap_interval(
    size: int,
    statistic: Callable[[Sequence[int]], float | None],
    *,
    seed: int,
    resamples: int = RESAMPLES,
    level: float = LEVEL,
) -> Interval | None:
    """The percentile interval of `statistic` over `resamples` resamples of `size` positions.

    A resample where the statistic is undefined (None: a label nobody has in it) is left out and
    counted; None when no resample gives a value.
    """
    if size < 1:
        raise ValueError("no articles to resample")
    rng = random.Random(seed)  # noqa: S311 - a seeded resampling meant to be reproducible
    values = sorted(
        value
        for value in (
            statistic([rng.randrange(size) for _ in range(size)]) for _ in range(resamples)
        )
        if value is not None
    )
    if not values:
        return None
    tail = (1 - level) / 2
    return Interval(_percentile(values, tail), _percentile(values, 1 - tail), len(values))


def _percentile(sorted_values: Sequence[float], q: float) -> float:
    """The value at rank q of the sorted values, by linear interpolation between neighbours (the
    default of numpy and of most statistics packages)."""
    position = q * (len(sorted_values) - 1)
    below = int(position)
    above = min(below + 1, len(sorted_values) - 1)
    weight = position - below
    return sorted_values[below] * (1 - weight) + sorted_values[above] * weight
