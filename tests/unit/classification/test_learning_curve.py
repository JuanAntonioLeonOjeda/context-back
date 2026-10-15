"""The splits of the learning curve: disjoint, nested, stratified and reproducible."""

from collections import Counter

import pytest

from datos.classification.domain.learning_curve import CurveSplit, curve_splits
from datos.classification.domain.training_set import LabelledExample, TrainingSetError


def labelled_set(random_count: int = 200, enriched_count: int = 200) -> list[LabelledExample]:
    strata = ["random"] * random_count + ["enriched"] * enriched_count
    return [
        LabelledExample(i, frozenset(), frozenset(), stratum=s, unsure=False)
        for i, s in enumerate(strata, start=1)
    ]


def splits(
    examples: list[LabelledExample],
    *,
    run_folds: tuple[int, ...] = (0, 1, 2, 3),
    sizes: tuple[int, ...] = (100, 200, 300),
    seed: int = 7,
) -> list[CurveSplit]:
    return curve_splits(examples, folds=4, run_folds=run_folds, sizes=sizes, seed=seed)


def ids(examples: tuple[LabelledExample, ...]) -> set[int]:
    return {e.article_id for e in examples}


def test_held_out_folds_are_disjoint_and_cover_the_whole_set() -> None:
    held = {s.fold: ids(s.held_out) for s in splits(labelled_set())}

    assert sum(len(h) for h in held.values()) == 400
    assert set().union(*held.values()) == set(range(1, 401))


def test_no_article_both_trains_and_measures() -> None:
    for split in splits(labelled_set()):
        assert not ids(split.train) & ids(split.held_out)


def test_a_larger_subset_holds_the_smaller_one() -> None:
    by_fold: dict[int, list[CurveSplit]] = {}
    for split in splits(labelled_set()):
        by_fold.setdefault(split.fold, []).append(split)

    for fold_splits in by_fold.values():
        sizes = [len(s.train) for s in fold_splits]
        assert sizes == [100, 200, 300]
        assert ids(fold_splits[0].train) < ids(fold_splits[1].train) < ids(fold_splits[2].train)


def test_every_subset_and_fold_keeps_the_strata_in_proportion() -> None:
    for split in splits(labelled_set(random_count=300, enriched_count=100)):
        train = Counter(e.stratum for e in split.train)
        held = Counter(e.stratum for e in split.held_out)
        assert train["random"] == split.size * 3 // 4
        assert held == {"random": 75, "enriched": 25}


def test_the_same_seed_gives_the_same_splits_whatever_the_input_order() -> None:
    examples = labelled_set()

    assert splits(examples) == splits(list(reversed(examples)))
    assert splits(examples) != splits(examples, seed=8)


def test_a_fold_is_the_same_whichever_other_folds_run() -> None:
    examples = labelled_set()
    all_folds = [s for s in splits(examples) if s.fold == 2]

    assert splits(examples, run_folds=(2,)) == all_folds


def test_refuses_a_size_larger_than_what_is_left_to_train() -> None:
    with pytest.raises(TrainingSetError, match="exceed the 300"):
        splits(labelled_set(), sizes=(100, 301))


def test_refuses_a_fold_that_does_not_exist() -> None:
    with pytest.raises(TrainingSetError, match=r"0\.\.3"):
        splits(labelled_set(), run_folds=(0, 4))
