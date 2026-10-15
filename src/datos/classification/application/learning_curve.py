"""Use case: the learning curve of the own model, inside the training set (ADR-0016).

For each split of `domain/learning_curve.py`, the model is trained on the subset and scored on the
held-out fold with the metrics of the evaluation. Nothing is saved but the scores: these models are
only a measurement. Every point is stored as soon as it ends, so a run cut short, or one that adds
folds another day, carries on from the stored points instead of training them again.
"""

from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Protocol

from datos.classification.application.train_model import (
    ArticleTextReader,
    TrainingConfig,
    TrainingSetInfo,
)
from datos.classification.domain.learning_curve import CurveSplit, curve_splits
from datos.classification.domain.metrics import FamilyScore, family_scores
from datos.classification.domain.text import article_text
from datos.classification.domain.training_set import (
    LabelledExample,
    TrainingSetError,
    check_usable,
    model_labels,
    multi_hot,
)


class ScoringModel(Protocol):
    def predict_proba(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        """One row per text, one probability per label, in the order of the labels trained on."""
        ...


class CurveTrainer(Protocol):
    def train(
        self,
        *,
        texts: Sequence[str],
        targets: Sequence[Sequence[int]],
        labels: Sequence[str],
        config: TrainingConfig,
    ) -> ScoringModel: ...


@dataclass(frozen=True, slots=True)
class CurveSettings:
    training_set: TrainingSetInfo
    config: TrainingConfig
    folds: int
    threshold: float

    def key(self) -> dict[str, object]:
        """What a stored point must share with this run to be reused: the labels, the training,
        the folds and the threshold. Not the sizes nor the folds run: those only add points."""
        return {
            "training_set": asdict(self.training_set),
            "training": asdict(self.config),
            "folds": self.folds,
            "threshold": self.threshold,
        }


@dataclass(frozen=True, slots=True)
class CurvePoint:
    fold: int
    size: int
    scores: tuple[FamilyScore, ...]
    training_seconds: float
    settings: Mapping[str, object]


class CurveStore(Protocol):
    def points(self) -> Sequence[CurvePoint]: ...

    def add(self, point: CurvePoint) -> None: ...


@dataclass(frozen=True, slots=True)
class CurvePlan:
    labels: tuple[str, ...]
    texts: Mapping[int, str]  # the model's input for every labelled article
    done: tuple[CurvePoint, ...]
    pending: tuple[CurveSplit, ...]

    def training_inputs(self, split: CurveSplit) -> tuple[list[str], list[list[int]]]:
        """The texts and multi-hot targets the model is trained on for `split`."""
        return (
            [self.texts[e.article_id] for e in split.train],
            [multi_hot(e, self.labels) for e in split.train],
        )


def plan_curve(
    *,
    examples: Sequence[LabelledExample],
    settings: CurveSettings,
    run_folds: Sequence[int],
    sizes: Sequence[int],
    sector_ids: Collection[str],
    test_ids: Collection[int],
    texts: ArticleTextReader,
    store: CurveStore,
) -> CurvePlan:
    """The checks, the splits and which of them are already measured, without training."""
    check_usable(examples, test_ids)
    stored = tuple(store.points())
    foreign = [(p.fold, p.size) for p in stored if p.settings != settings.key()]
    if foreign:
        # Mixing them would draw one curve from two trainings; a new run needs its own file.
        raise TrainingSetError(f"stored points measured with other settings: {foreign[:5]}")

    measured = {(p.fold, p.size) for p in stored}
    splits = curve_splits(
        examples,
        folds=settings.folds,
        run_folds=run_folds,
        sizes=sizes,
        seed=settings.config.seed,
    )
    return CurvePlan(
        labels=model_labels(sector_ids),
        texts=_model_inputs(examples, texts),
        done=stored,
        pending=tuple(s for s in splits if (s.fold, s.size) not in measured),
    )


def run_curve(
    plan: CurvePlan,
    *,
    trainer: CurveTrainer,
    store: CurveStore,
    settings: CurveSettings,
    timer: Callable[[], float],
    on_point: Callable[[CurvePoint], None],
) -> list[CurvePoint]:
    """Trains and scores every pending split, storing each point before the next one starts."""
    points: list[CurvePoint] = []
    for split in plan.pending:
        point = _measure(split, plan, trainer=trainer, settings=settings, timer=timer)
        store.add(point)
        on_point(point)
        points.append(point)
    return points


def _measure(
    split: CurveSplit,
    plan: CurvePlan,
    *,
    trainer: CurveTrainer,
    settings: CurveSettings,
    timer: Callable[[], float],
) -> CurvePoint:
    train_texts, targets = plan.training_inputs(split)
    started = timer()
    model = trainer.train(
        texts=train_texts, targets=targets, labels=plan.labels, config=settings.config
    )
    seconds = timer() - started

    rows = model.predict_proba([plan.texts[e.article_id] for e in split.held_out])
    predicted = [
        frozenset(
            label
            for label, p in zip(plan.labels, row, strict=True)
            if p >= settings.threshold  # "at least", as the classifier applies it
        )
        for row in rows
    ]
    gold = [
        frozenset(
            label for label, hot in zip(plan.labels, multi_hot(e, plan.labels), strict=True) if hot
        )
        for e in split.held_out
    ]
    return CurvePoint(
        fold=split.fold,
        size=split.size,
        scores=family_scores(gold, predicted, plan.labels),
        training_seconds=round(seconds, 1),
        settings=settings.key(),
    )


def _model_inputs(examples: Sequence[LabelledExample], reader: ArticleTextReader) -> dict[int, str]:
    ids = sorted(e.article_id for e in examples)
    found = reader.texts(ids)
    missing = [i for i in ids if i not in found]
    if missing:
        raise TrainingSetError(f"articles not in the database: {missing[:5]}")
    return {i: article_text(found[i].headline, found[i].lead) for i in ids}
