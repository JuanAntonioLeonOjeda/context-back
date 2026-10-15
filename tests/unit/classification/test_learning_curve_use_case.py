"""The learning curve use case, with a fake trainer: what is trained, scored, stored and resumed."""

from collections.abc import Collection, Mapping, Sequence
from dataclasses import replace

import pytest

from datos.classification.application.learning_curve import (
    CurvePlan,
    CurvePoint,
    CurveSettings,
    plan_curve,
    run_curve,
)
from datos.classification.application.store_classifications import ArticleText
from datos.classification.application.train_model import TrainingConfig, TrainingSetInfo
from datos.classification.domain.training_set import LabelledExample, TrainingSetError

SETTINGS = CurveSettings(
    training_set=TrainingSetInfo("train-set-v1", "abc123"),
    config=TrainingConfig(encoder="encoder", seed=42),
    folds=4,
    threshold=0.5,
)
SIZES = (10, 20, 30)
# Even articles are about health, odd ones about nothing the model learns.
EXAMPLES = [
    LabelledExample(
        i,
        frozenset({"health"}) if i % 2 == 0 else frozenset(),
        frozenset(),
        stratum="random" if i <= 20 else "enriched",
        unsure=False,
    )
    for i in range(1, 41)
]
HEALTH = {f"headline {i}" for i in range(2, 41, 2)}


class Texts:
    def __init__(self, missing: Collection[int] = ()) -> None:
        self._missing = set(missing)

    def texts(self, article_ids: Collection[int]) -> Mapping[int, ArticleText]:
        return {
            i: ArticleText(i, f"headline {i}", None) for i in article_ids if i not in self._missing
        }


class KnowingModel:
    """Gives `probability` to health when the article is about health, 0 to everything else."""

    def __init__(self, labels: Sequence[str], probability: float) -> None:
        self._labels = labels
        self._probability = probability

    def predict_proba(self, texts: Sequence[str]) -> list[list[float]]:
        return [
            [
                self._probability if label == "sector:health" and t in HEALTH else 0.0
                for label in self._labels
            ]
            for t in texts
        ]


class Trainer:
    def __init__(self, probability: float = 0.9) -> None:
        self.probability = probability
        self.trained_on: list[list[str]] = []

    def train(
        self,
        *,
        texts: Sequence[str],
        targets: Sequence[Sequence[int]],
        labels: Sequence[str],
        config: TrainingConfig,
    ) -> KnowingModel:
        self.trained_on.append(list(texts))
        return KnowingModel(labels, self.probability)


class Store:
    def __init__(self, points: Sequence[CurvePoint] = ()) -> None:
        self.stored = list(points)

    def points(self) -> Sequence[CurvePoint]:
        return list(self.stored)

    def add(self, point: CurvePoint) -> None:
        self.stored.append(point)


def plan(
    store: Store, *, run_folds: Sequence[int] = (0, 1), texts: Texts | None = None
) -> CurvePlan:
    return plan_curve(
        examples=EXAMPLES,
        settings=SETTINGS,
        run_folds=run_folds,
        sizes=SIZES,
        sector_ids={"health", "education"},
        test_ids={900},
        texts=texts or Texts(),
        store=store,
    )


def run(the_plan: CurvePlan, store: Store, trainer: Trainer) -> list[CurvePoint]:
    clock = iter(float(t) for t in range(0, 1000, 5))  # each training takes 5 "seconds"
    return run_curve(
        the_plan,
        trainer=trainer,
        store=store,
        settings=SETTINGS,
        timer=lambda: next(clock),
        on_point=lambda _: None,
    )


def macro(point: CurvePoint, family: str) -> float | None:
    return next(s.macro_f1 for s in point.scores if s.family == family)


def test_measures_every_size_of_the_folds_run_and_stores_each_point() -> None:
    store = Store()

    points = run(plan(store), store, Trainer())

    assert [(p.fold, p.size) for p in points] == [
        (0, 10),
        (0, 20),
        (0, 30),
        (1, 10),
        (1, 20),
        (1, 30),
    ]
    assert store.stored == points
    assert {p.training_seconds for p in points} == {5.0}


def test_trains_on_the_subset_and_scores_on_the_held_out_fold_only() -> None:
    store = Store()
    the_plan = plan(store)
    trainer = Trainer()

    run(the_plan, store, trainer)

    for split, texts in zip(the_plan.pending, trainer.trained_on, strict=True):
        held_out = {f"headline {e.article_id}" for e in split.held_out}
        assert len(texts) == split.size
        assert not held_out & set(texts)


def test_a_model_that_knows_the_answer_scores_one_and_an_absent_label_stays_out() -> None:
    store = Store()

    point = run(plan(store), store, Trainer())[0]

    assert macro(point, "sector") == 1.0  # health right everywhere; education nobody has
    assert macro(point, "level") is None  # no article has a level, and none is predicted


def test_a_probability_equal_to_the_threshold_gives_the_label() -> None:
    at, below = Store(), Store()

    assert macro(run(plan(at), at, Trainer(0.5))[0], "sector") == 1.0
    assert macro(run(plan(below), below, Trainer(0.49))[0], "sector") == 0.0


def test_resumes_from_the_stored_points_without_training_them_again() -> None:
    first = Store()
    run(plan(first, run_folds=(0,)), first, Trainer())
    trainer = Trainer()

    resumed = plan(first, run_folds=(0, 1))
    run(resumed, first, trainer)

    assert [(s.fold, s.size) for s in resumed.pending] == [(1, 10), (1, 20), (1, 30)]
    assert len(trainer.trained_on) == 3
    assert len(first.stored) == 6


def test_refuses_points_stored_with_other_settings() -> None:
    store = Store()
    run(plan(store, run_folds=(0,)), store, Trainer())
    store.stored[0] = replace(store.stored[0], settings={**store.stored[0].settings, "folds": 5})

    with pytest.raises(TrainingSetError, match=r"other settings: \[\(0, 10\)\]"):
        plan(store)


def test_refuses_an_article_missing_from_the_database() -> None:
    with pytest.raises(TrainingSetError, match=r"not in the database: \[7\]"):
        plan(Store(), texts=Texts(missing={7}))
