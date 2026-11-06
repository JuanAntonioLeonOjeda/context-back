"""Use case: train the own model on the hand-labelled training set (ADR-0016).

The training itself is behind a port, so this orchestration (the labels, the texts, the checks, the
frozen model directory and the model's card) is tested without SetFit. Evaluation is not here: it
happens on the blind test set (task 18), and this module never reads it except for its ids, to
refuse a training set that shares an article with it.
"""

import json
from collections import Counter
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from datos.classification.application.store_classifications import ArticleText
from datos.classification.domain.text import article_text
from datos.classification.domain.training_set import (
    LabelledExample,
    TrainingSetError,
    check_usable,
    model_labels,
    multi_hot,
)

CARD_FILE = "model-card.json"


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    """Every hyperparameter, written out: the library's defaults are not trusted to stay put.

    The values are SetFit 1.2.0's, except `num_iterations`. Left unset, SetFit draws every sentence
    pair (`sampling_strategy="oversampling"`): 89,168 pairs for 400 examples, about 13 hours on the
    author's Mac (8.6 s per step of 16 pairs, measured 2026-10-15). 20 pairs-iterations, SetFit's
    value before 1.0, is 16,000 pairs, about 2.4 hours. The classifier head is logistic regression,
    so SetFit's head epochs and batch size do not apply.
    """

    encoder: str
    seed: int
    num_epochs: int = 1
    batch_size: int = 16
    body_learning_rate: float = 2e-5
    sampling_strategy: str = "oversampling"
    num_iterations: int | None = 20


class TrainedModel(Protocol):
    environment: Mapping[str, str]  # the device and the library versions it was trained with

    def save(self, directory: Path) -> None: ...


class ModelTrainer(Protocol):
    def train(
        self,
        *,
        texts: Sequence[str],
        targets: Sequence[Sequence[int]],
        labels: Sequence[str],
        config: TrainingConfig,
    ) -> TrainedModel: ...


class ArticleTextReader(Protocol):
    def texts(self, article_ids: Collection[int]) -> Mapping[int, ArticleText]: ...


class ModelStore(Protocol):
    """Where trained models live. A model, once stored, is frozen: a new one gets a new name."""

    def exists(self, name: str) -> bool: ...

    def save(self, name: str, model: TrainedModel) -> str:
        """Writes the model under `name` and returns its version, a hash of the files."""
        ...

    def write_card(self, name: str, card: str) -> None: ...


@dataclass(frozen=True, slots=True)
class TrainingSetInfo:
    name: str  # "train-set-v1"
    file_hash: str  # a hash of the file, so the card says exactly which labels were used


@dataclass(frozen=True, slots=True)
class ModelCard:
    """What is needed to repeat the training and to say what a model is: what MLflow would log."""

    name: str
    model_id: str
    model_version: str
    labels: tuple[str, ...]
    threshold: float
    encoder: str
    training_set: Mapping[str, object]
    training: Mapping[str, object]
    environment: Mapping[str, str]
    training_seconds: float
    trained_at: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def model_name(training_set: TrainingSetInfo, config: TrainingConfig) -> str:
    return f"{training_set.name}-{config.encoder.rsplit('/', 1)[-1]}-seed{config.seed}"


@dataclass(frozen=True, slots=True)
class TrainingPlan:
    """Everything decided before any training: shown to the author first, and what a dry run is."""

    name: str
    labels: tuple[str, ...]
    texts: tuple[str, ...]
    targets: tuple[tuple[int, ...], ...]
    description: Mapping[str, object]  # the training set as the card will describe it


def plan_training(
    *,
    examples: Sequence[LabelledExample],
    training_set: TrainingSetInfo,
    sector_ids: Collection[str],
    test_ids: Collection[int],
    texts: ArticleTextReader,
    tag_stoplist: str,
    store: ModelStore,
    config: TrainingConfig,
) -> TrainingPlan:
    """The checks, the texts and the labels, without training or storing anything."""
    check_usable(examples, test_ids)
    name = model_name(training_set, config)
    if store.exists(name):
        raise TrainingSetError(f"the model {name} exists: a stored model is frozen")

    ordered = sorted(examples, key=lambda e: e.article_id)  # the order is part of reproducibility
    found = texts.texts([e.article_id for e in ordered])
    missing = [e.article_id for e in ordered if e.article_id not in found]
    if missing:
        raise TrainingSetError(f"articles not in the database: {missing[:5]}")

    labels = model_labels(sector_ids)
    return TrainingPlan(
        name=name,
        labels=labels,
        texts=tuple(
            article_text(
                found[e.article_id].headline, found[e.article_id].lead, found[e.article_id].tags
            )
            for e in ordered
        ),
        targets=tuple(tuple(multi_hot(e, labels)) for e in ordered),
        description={
            "name": training_set.name,
            "file_hash": training_set.file_hash,
            "tag_stoplist": tag_stoplist,  # the tags the texts were built without
        }
        | _describe(ordered, labels),
    )


def fit_model(
    plan: TrainingPlan,
    *,
    trainer: ModelTrainer,
    store: ModelStore,
    config: TrainingConfig,
    threshold: float,
    now: Callable[[], datetime],
    timer: Callable[[], float],
) -> ModelCard:
    started = timer()
    model = trainer.train(texts=plan.texts, targets=plan.targets, labels=plan.labels, config=config)
    seconds = timer() - started

    version = store.save(plan.name, model)
    card = ModelCard(
        name=plan.name,
        model_id="setfit",
        model_version=version,
        labels=plan.labels,
        threshold=threshold,
        encoder=config.encoder,
        training_set=plan.description,
        training=asdict(config),
        environment=dict(model.environment),
        training_seconds=round(seconds, 1),
        trained_at=now().isoformat(),
    )
    store.write_card(plan.name, card.to_json())
    return card


def train_model(
    *,
    examples: Sequence[LabelledExample],
    training_set: TrainingSetInfo,
    sector_ids: Collection[str],
    test_ids: Collection[int],
    texts: ArticleTextReader,
    tag_stoplist: str,
    trainer: ModelTrainer,
    store: ModelStore,
    config: TrainingConfig,
    threshold: float,
    now: Callable[[], datetime],
    timer: Callable[[], float],
) -> ModelCard:
    plan = plan_training(
        examples=examples,
        training_set=training_set,
        sector_ids=sector_ids,
        test_ids=test_ids,
        texts=texts,
        tag_stoplist=tag_stoplist,
        store=store,
        config=config,
    )
    return fit_model(
        plan, trainer=trainer, store=store, config=config, threshold=threshold, now=now, timer=timer
    )


def _describe(examples: Sequence[LabelledExample], labels: Sequence[str]) -> dict[str, object]:
    """How many examples, and of each stratum and label: what a reader checks first."""
    positives = Counter(
        label
        for e in examples
        for label, hot in zip(labels, multi_hot(e, labels), strict=True)
        if hot
    )
    return {
        "size": len(examples),
        "unsure": sum(e.unsure for e in examples),
        "no_label": sum(not (e.sectors or e.levels) for e in examples),
        "per_stratum": dict(sorted(Counter(e.stratum for e in examples).items())),
        "per_label": {label: positives.get(label, 0) for label in labels},
    }
