"""The learning curve's splits (ADR-0016): for each point, which articles train and which measure.

Pure: the labelled examples and a seed in, the splits out. The training set is dealt into folds,
keeping the strata in proportion; with one fold held out, the model is trained on nested subsets of
the rest. Nested means the subset of 200 holds the 100 of the smaller one plus 100 more, so the
curve shows what more labels add, not what different labels do.
"""

import random
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from datos.classification.domain.metrics import FamilyScore
from datos.classification.domain.training_set import LabelledExample, TrainingSetError


@dataclass(frozen=True, slots=True)
class CurveSplit:
    """One point of the curve: train on `train`, measure on `held_out`."""

    fold: int
    size: int
    train: tuple[LabelledExample, ...]
    held_out: tuple[LabelledExample, ...]


def _shuffled_by_stratum(
    examples: Sequence[LabelledExample], rng: random.Random
) -> dict[str, list[LabelledExample]]:
    by_stratum: dict[str, list[LabelledExample]] = defaultdict(list)
    for example in sorted(examples, key=lambda e: e.article_id):  # input order must not matter
        by_stratum[example.stratum].append(example)
    for stratum in sorted(by_stratum):  # shuffled in a fixed order, so the seed decides alone
        rng.shuffle(by_stratum[stratum])
    return dict(sorted(by_stratum.items()))


def stratified_order(
    examples: Sequence[LabelledExample], rng: random.Random
) -> list[LabelledExample]:
    """The examples shuffled within each stratum, then interleaved so that every prefix keeps the
    strata in the proportion of the whole: the first 100 are as much random as the first 300."""
    by_stratum = _shuffled_by_stratum(examples, rng)
    taken = dict.fromkeys(by_stratum, 0)
    order: list[LabelledExample] = []
    while len(order) < len(examples):
        # The stratum furthest behind its share goes next; ties go to the first by name.
        stratum = min(
            (s for s in by_stratum if taken[s] < len(by_stratum[s])),
            key=lambda s: taken[s] / len(by_stratum[s]),
        )
        order.append(by_stratum[stratum][taken[stratum]])
        taken[stratum] += 1
    return order


def deal_folds(
    examples: Sequence[LabelledExample], folds: int, rng: random.Random
) -> list[list[LabelledExample]]:
    """Each stratum shuffled and dealt one by one to the folds, carrying on where the previous
    stratum stopped: every fold gets its share of each stratum, and sizes differ by one at most.

    Dealing the interleaved order instead would not do: with 300 random and 100 enriched it repeats
    every four articles, and dealt to four folds it puts every enriched article in the same one.
    """
    dealt: list[list[LabelledExample]] = [[] for _ in range(folds)]
    position = 0
    for members in _shuffled_by_stratum(examples, rng).values():
        for example in members:
            dealt[position % folds].append(example)
            position += 1
    return dealt


def curve_splits(
    examples: Sequence[LabelledExample],
    *,
    folds: int,
    run_folds: Sequence[int],
    sizes: Sequence[int],
    seed: int,
) -> list[CurveSplit]:
    """The splits for the folds in `run_folds`, each with every size, smallest first."""
    if not set(run_folds) <= set(range(folds)):
        raise TrainingSetError(f"folds to run must be in 0..{folds - 1}: {sorted(run_folds)}")
    dealt = deal_folds(examples, folds, random.Random(seed))  # noqa: S311 - seeded on purpose

    splits: list[CurveSplit] = []
    for fold in sorted(set(run_folds)):
        rest = [e for i, part in enumerate(dealt) if i != fold for e in part]
        # A seed of its own per fold: a fold's subsets are the same whichever other folds run,
        # so folds 2 and 3 can be added another day to a run of 0 and 1.
        rest = stratified_order(rest, random.Random(f"{seed}:{fold}"))  # noqa: S311 - as above
        too_big = [size for size in sizes if size > len(rest)]
        if too_big:
            raise TrainingSetError(f"sizes {too_big} exceed the {len(rest)} articles left to train")
        splits.extend(
            CurveSplit(fold, size, tuple(rest[:size]), tuple(dealt[fold])) for size in sorted(sizes)
        )
    return splits


# The rule of ADR-0016 (D12), set before any curve was seen: 100 more articles are labelled when
# the mean macro-F1 rises by at least 3 points from 200 to 300 in either family.
RISE_FROM_SIZE = 200
RISE_TO_SIZE = 300
MIN_RISE = 0.03  # F1 is in 0..1, so 3 points are 0.03


class ScoredPoint(Protocol):
    """A measured point as the summary reads it (the use case's `CurvePoint`)."""

    @property
    def fold(self) -> int: ...
    @property
    def size(self) -> int: ...
    @property
    def scores(self) -> tuple[FamilyScore, ...]: ...


@dataclass(frozen=True, slots=True)
class SizeSummary:
    family: str
    size: int
    mean_macro_f1: float | None  # over the folds where the family had a score
    fold_scores: tuple[float, ...]  # each fold's macro-F1, by fold: the spread is in plain view


@dataclass(frozen=True, slots=True)
class RiseVerdict:
    family: str
    rise: float | None  # mean over folds of (F1 at 300 - F1 at 200); None if no fold has both
    folds: int  # folds with both sizes scored: the rise compares the same folds only
    still_rises: bool | None  # None when it cannot be told: no fold measured both sizes


def summarise(points: Sequence[ScoredPoint]) -> tuple[SizeSummary, ...]:
    """The mean macro-F1 per family and size, families in their first order, sizes ascending."""
    table = _macro_by_family(points)
    return tuple(
        SizeSummary(family, size, _mean(list(by_fold.values())), tuple(by_fold.values()))
        for family, by_size in table.items()
        for size, by_fold in sorted(by_size.items())
    )


def rise_verdicts(points: Sequence[ScoredPoint]) -> tuple[RiseVerdict, ...]:
    """Whether each family still rises from 200 to 300, by the rule above.

    Paired by fold: a run cut after fold 1 reached 200 but not 300 must not compare the mean of
    two folds at 200 with one fold at 300, which would mix the size with the fold.
    """
    verdicts: list[RiseVerdict] = []
    for family, by_size in _macro_by_family(points).items():
        low, high = by_size.get(RISE_FROM_SIZE, {}), by_size.get(RISE_TO_SIZE, {})
        rises = [high[fold] - low[fold] for fold in sorted(low.keys() & high.keys())]
        rise = _mean(rises)
        # Rounded before comparing: 0.83 - 0.80 is 0.0299999… in floating point, and three
        # points must count as three points.
        verdict = None if rise is None else round(rise, 9) >= MIN_RISE
        verdicts.append(RiseVerdict(family, rise, len(rises), verdict))
    return tuple(verdicts)


def _macro_by_family(points: Sequence[ScoredPoint]) -> dict[str, dict[int, dict[int, float]]]:
    """family → size → fold → macro-F1, leaving out a family with no score in that point."""
    table: dict[str, dict[int, dict[int, float]]] = {}
    for point in sorted(points, key=lambda p: (p.fold, p.size)):
        for score in point.scores:
            by_size = table.setdefault(score.family, {})
            if score.macro_f1 is not None:
                by_size.setdefault(point.size, {})[point.fold] = score.macro_f1
    return table


def _mean(values: Sequence[float]) -> float | None:
    return sum(values) / len(values) if values else None
