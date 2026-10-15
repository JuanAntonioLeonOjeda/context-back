"""The training job's orchestration, with a fake trainer: no SetFit, no network, no database."""

import json
from collections.abc import Collection, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

import pytest

from datos.classification.application.store_classifications import ArticleText
from datos.classification.application.train_model import (
    CARD_FILE,
    ModelCard,
    TrainedModel,
    TrainingConfig,
    TrainingSetInfo,
    model_name,
    plan_training,
    train_model,
)
from datos.classification.domain.training_set import LabelledExample, TrainingSetError
from datos.classification.infrastructure.local_model_store import (
    LocalModelStore,
    directory_hash,
)
from datos.governments.application.published import CompetenceLevel

SECTORS = ["housing", "education", "health"]
STATE = CompetenceLevel.STATE
INFO = TrainingSetInfo("train-set-v1", "abc123def456")
CONFIG = TrainingConfig(
    encoder="sentence-transformers/paraphrase-multilingual-mpnet-base-v2", seed=42
)
NOW = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)


class FakeModel:
    environment: Mapping[str, str] = {"device": "mps", "setfit": "1.2.0"}

    def __init__(self, weights: bytes) -> None:
        self._weights = weights

    def save(self, directory: Path) -> None:
        (directory / "weights.bin").write_bytes(self._weights)
        (directory / "labels.txt").write_text("sector:education\n", encoding="utf-8")


class FakeTrainer:
    def __init__(self, weights: bytes = b"w1") -> None:
        self.weights = weights
        self.calls: list[dict[str, object]] = []

    def train(
        self,
        *,
        texts: Sequence[str],
        targets: Sequence[Sequence[int]],
        labels: Sequence[str],
        config: TrainingConfig,
    ) -> TrainedModel:
        self.calls.append(
            {"texts": list(texts), "targets": [list(t) for t in targets], "labels": list(labels)}
        )
        return FakeModel(self.weights)


class FakeTexts:
    def __init__(self, articles: Mapping[int, tuple[str, str | None]]) -> None:
        self._articles = {i: ArticleText(i, h, lead) for i, (h, lead) in articles.items()}

    def texts(self, article_ids: Collection[int]) -> Mapping[int, ArticleText]:
        return {i: self._articles[i] for i in article_ids if i in self._articles}


def example(article_id: int, sectors: set[str], levels: set[CompetenceLevel]) -> LabelledExample:
    return LabelledExample(article_id, frozenset(sectors), frozenset(levels), "random", False)


EXAMPLES = [
    example(30, {"housing"}, set()),
    example(10, {"health"}, {STATE}),
    example(20, set(), set()),
]
ARTICLES = {10: ("Sanidad amplía", "Hospitales."), 20: ("Un partido", None), 30: ("Alquiler", "")}


def run(
    tmp_path: Path,
    trainer: FakeTrainer | None = None,
    examples: Sequence[LabelledExample] = EXAMPLES,
    test_ids: Collection[int] = (),
    articles: Mapping[int, tuple[str, str | None]] = ARTICLES,
) -> tuple[ModelCard, FakeTrainer]:
    trainer = trainer or FakeTrainer()
    timer = iter([0.0, 18.04])
    card = train_model(
        examples=examples,
        training_set=INFO,
        sector_ids=SECTORS,
        test_ids=test_ids,
        texts=FakeTexts(articles),
        trainer=trainer,
        store=LocalModelStore(tmp_path),
        config=CONFIG,
        threshold=0.5,
        now=lambda: NOW,
        timer=lambda: next(timer),
    )
    return card, trainer


def test_trains_on_the_texts_and_labels_in_article_id_order(tmp_path: Path) -> None:
    _, trainer = run(tmp_path)

    [call] = trainer.calls
    assert call["texts"] == ["Sanidad amplía Hospitales.", "Un partido", "Alquiler"]
    assert call["labels"] == [
        "sector:education",
        "sector:health",
        "sector:housing",
        "level:state",
        "level:ccaa",
        "level:local",
    ]
    assert call["targets"] == [
        [0, 1, 0, 1, 0, 0],  # article 10: health, state
        [0, 0, 0, 0, 0, 0],  # article 20: nothing, a negative example
        [0, 0, 1, 0, 0, 0],  # article 30: housing
    ]


def test_the_order_the_examples_come_in_does_not_change_what_the_model_is_trained_on(
    tmp_path: Path,
) -> None:
    _, forward = run(tmp_path / "a", examples=EXAMPLES)
    _, backward = run(tmp_path / "b", examples=list(reversed(EXAMPLES)))

    assert forward.calls == backward.calls


def test_the_model_is_stored_under_a_name_that_says_how_it_was_made(tmp_path: Path) -> None:
    card, _ = run(tmp_path)

    assert card.name == "train-set-v1-paraphrase-multilingual-mpnet-base-v2-seed42"
    assert model_name(INFO, CONFIG) == card.name
    assert (tmp_path / card.name / "weights.bin").read_bytes() == b"w1"


def test_the_version_is_a_hash_of_the_files_and_changes_with_them(tmp_path: Path) -> None:
    first, _ = run(tmp_path / "a", FakeTrainer(b"w1"))
    again, _ = run(tmp_path / "b", FakeTrainer(b"w1"))
    other, _ = run(tmp_path / "c", FakeTrainer(b"w2"))

    assert first.model_version == again.model_version == directory_hash(tmp_path / "a" / first.name)
    assert other.model_version != first.model_version
    assert len(first.model_version) == 12


def test_the_card_leaves_the_card_out_of_the_hash_it_names(tmp_path: Path) -> None:
    card, _ = run(tmp_path)

    # Writing the card after the hash must not change what the hash says.
    assert directory_hash(tmp_path / card.name) == card.model_version


def test_the_card_says_what_is_needed_to_repeat_the_training(tmp_path: Path) -> None:
    run(tmp_path)

    card = json.loads(
        (
            tmp_path / "train-set-v1-paraphrase-multilingual-mpnet-base-v2-seed42" / CARD_FILE
        ).read_text()
    )

    assert card["model_id"] == "setfit"
    assert card["threshold"] == 0.5
    assert card["encoder"] == CONFIG.encoder
    assert card["training"] == {
        "encoder": CONFIG.encoder,
        "seed": 42,
        "num_epochs": 1,
        "batch_size": 16,
        "body_learning_rate": 2e-5,
        "sampling_strategy": "oversampling",
        "num_iterations": 20,
    }
    assert card["environment"] == {"device": "mps", "setfit": "1.2.0"}
    assert card["training_seconds"] == 18.0
    assert card["trained_at"] == "2026-10-21T12:00:00+00:00"
    assert card["training_set"] == {
        "name": "train-set-v1",
        "file_hash": "abc123def456",
        "size": 3,
        "unsure": 0,
        "no_label": 1,
        "per_stratum": {"random": 3},
        "per_label": {
            "sector:education": 0,
            "sector:health": 1,
            "sector:housing": 1,
            "level:state": 1,
            "level:ccaa": 0,
            "level:local": 0,
        },
    }


def test_a_training_set_that_shares_an_article_with_the_test_set_is_refused(tmp_path: Path) -> None:
    with pytest.raises(TrainingSetError, match="blind test set"):
        run(tmp_path, test_ids={20})

    assert not list(tmp_path.iterdir())  # nothing trained, nothing stored


def test_an_article_missing_from_the_database_is_refused_before_training(tmp_path: Path) -> None:
    trainer = FakeTrainer()

    with pytest.raises(TrainingSetError, match=r"not in the database: \[20\]"):
        run(tmp_path, trainer, articles={10: ARTICLES[10], 30: ARTICLES[30]})

    assert trainer.calls == []


def test_a_stored_model_is_frozen_and_a_second_training_is_refused(tmp_path: Path) -> None:
    run(tmp_path)
    trainer = FakeTrainer(b"other")

    with pytest.raises(TrainingSetError, match="frozen"):
        run(tmp_path, trainer)

    assert trainer.calls == []


def test_a_plan_is_made_without_training_or_storing_anything(tmp_path: Path) -> None:
    trainer = FakeTrainer()

    plan = plan_training(
        examples=EXAMPLES,
        training_set=INFO,
        sector_ids=SECTORS,
        test_ids=(),
        texts=FakeTexts(ARTICLES),
        store=LocalModelStore(tmp_path),
        config=CONFIG,
    )

    assert plan.name == model_name(INFO, CONFIG)
    assert plan.texts == ("Sanidad amplía Hospitales.", "Un partido", "Alquiler")
    assert plan.targets[0] == (0, 1, 0, 1, 0, 0)
    assert plan.description["size"] == 3
    assert trainer.calls == []
    assert not list(tmp_path.iterdir())  # nothing stored


def test_a_plan_makes_the_same_checks_as_a_training(tmp_path: Path) -> None:
    with pytest.raises(TrainingSetError, match="blind test set"):
        plan_training(
            examples=EXAMPLES,
            training_set=INFO,
            sector_ids=SECTORS,
            test_ids={10},
            texts=FakeTexts(ARTICLES),
            store=LocalModelStore(tmp_path),
            config=CONFIG,
        )


def test_the_pairs_per_example_default_to_the_value_that_can_be_run_in_hours() -> None:
    # SetFit's own default (every pair) is 89,168 pairs for 400 examples, about 13 hours.
    assert CONFIG.num_iterations == 20
