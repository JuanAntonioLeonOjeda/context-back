"""The own model with SetFit itself (ADR-0016): `uv run pytest -m ml`.

Needs the `ml` group and downloads the encoder the first time (about 1.2 GB into the Hugging Face
cache). It trains a tiny model on made-up headlines, so it checks that the pieces fit (training,
saving, loading, the labels surviving, the adapter reading it), not that the model is any good: that
is the evaluation of task 18, on the blind test set. Never runs in CI.
"""

import time
from collections.abc import Collection, Sequence
from pathlib import Path

import pytest

from datos.classification.infrastructure.setfit_classifier import SetFitClassifier
from datos.classification.infrastructure.setfit_predictor import SetFitPredictor

pytestmark = pytest.mark.ml

ENCODER = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
LABELS = ["sector:education", "sector:health", "sector:housing", "level:state", "level:ccaa"]
SECTORS = frozenset({"education", "health", "housing"})
# (text, sector, level): invented, in Spanish and Catalan, only to give the model something to fit.
EXAMPLES = [
    ("La Consejería amplía las plazas de infantil en los colegios públicos", 0, 1),
    ("El Ministerio de Educación aprueba el nuevo currículo de secundaria", 0, 3),
    ("La Generalitat convoca ajudes per a la matrícula universitària", 0, 1),
    ("El sindicato docente pide más profesores de apoyo en las aulas", 0, 1),
    ("El Servicio de Salud reduce las listas de espera en los hospitales", 1, 1),
    ("El Gobierno aprueba la ley de medicamentos y farmacia", 1, 3),
    ("Sanitat obre un nou centre d'atenció primària al barri", 1, 1),
    ("Los médicos de urgencias denuncian la falta de personal en el hospital", 1, 1),
    ("La comunidad destina fondos a viviendas públicas de alquiler asequible", 2, 1),
    ("El Estado prorroga las ayudas al alquiler para jóvenes", 2, 3),
    ("El Govern declara noves zones tensionades de lloguer", 2, 1),
    ("El sindicato de inquilinos exige frenar los desahucios", 2, 1),
]


def _rows() -> dict[str, list[object]]:
    rows: dict[str, list[object]] = {"text": [], "label": []}
    for text, sector, level in EXAMPLES:
        multi_hot = [0] * len(LABELS)
        multi_hot[sector] = 1
        multi_hot[level] = 1
        rows["text"].append(text)
        rows["label"].append(multi_hot)
    return rows


@pytest.fixture(scope="module")
def saved_model(tmp_path_factory: pytest.TempPathFactory) -> Path:
    from datasets import Dataset
    from setfit import SetFitModel, Trainer, TrainingArguments

    started = time.perf_counter()
    model = SetFitModel.from_pretrained(ENCODER, multi_target_strategy="one-vs-rest", labels=LABELS)
    directory = tmp_path_factory.mktemp("setfit-model")
    # output_dir: SetFit writes checkpoints to ./checkpoints by default, into the repository.
    args = TrainingArguments(
        batch_size=8,
        num_epochs=1,
        num_iterations=4,
        seed=42,
        output_dir=str(directory / "checkpoints"),
    )
    Trainer(model=model, args=args, train_dataset=Dataset.from_dict(_rows())).train()
    model.save_pretrained(str(directory))
    print(f"\ntrained and saved in {time.perf_counter() - started:.0f} s")
    return directory


def test_a_trained_model_is_loaded_with_its_label_names(saved_model: Path) -> None:
    predictor = SetFitPredictor.load(saved_model)

    probabilities = predictor.probabilities("El hospital amplía la plantilla")

    assert list(probabilities) == LABELS  # the names and their order survived saving
    assert all(0.0 <= p <= 1.0 for p in probabilities.values())


def test_the_same_text_gets_the_same_probabilities(saved_model: Path) -> None:
    predictor = SetFitPredictor.load(saved_model)

    assert predictor.probabilities("Ayudas al alquiler") == predictor.probabilities(
        "Ayudas al alquiler"
    )


def test_the_adapter_reads_it_and_speaks_the_projects_vocabulary(saved_model: Path) -> None:
    classifier = SetFitClassifier(
        SetFitPredictor.load(saved_model), model_version="test", sector_ids=SECTORS
    )

    labels = classifier.classify("El Gobierno aprueba una ley", "Sobre la sanidad pública.")

    assert labels.communities == frozenset()
    assert labels.sectors <= SECTORS
    assert {score.label for score in labels.scores} <= set(LABELS)


def test_the_training_job_trains_stores_and_describes_a_model_that_can_be_loaded(
    tmp_path: Path,
) -> None:
    """The whole use case with the real trainer: examples in, a frozen model directory out."""
    from datetime import UTC, datetime

    from datos.classification.application.store_classifications import ArticleText
    from datos.classification.application.train_model import (
        CARD_FILE,
        TrainingConfig,
        TrainingSetInfo,
        train_model,
    )
    from datos.classification.domain.training_set import LabelledExample, model_labels
    from datos.classification.infrastructure.local_model_store import (
        LocalModelStore,
        directory_hash,
    )
    from datos.classification.infrastructure.setfit_trainer import SetFitModelTrainer
    from datos.governments.application.published import CompetenceLevel

    sector_of = {0: "education", 1: "health", 2: "housing"}
    level_of = {1: CompetenceLevel.CCAA, 3: CompetenceLevel.STATE}
    examples = [
        LabelledExample(i, frozenset({sector_of[s]}), frozenset({level_of[lv]}), "random", False)
        for i, (_, s, lv) in enumerate(EXAMPLES, start=1)
    ]
    articles = {i: ArticleText(i, text, None) for i, (text, _, _) in enumerate(EXAMPLES, start=1)}

    class Texts:
        def texts(self, article_ids: Collection[int]) -> dict[int, ArticleText]:
            return {i: articles[i] for i in article_ids}

    cwd_before = {p.name for p in Path.cwd().iterdir()}
    card = train_model(
        examples=examples,
        training_set=TrainingSetInfo("toy-set", "0123456789ab"),
        sector_ids=SECTORS,
        test_ids=set(),
        texts=Texts(),
        tag_stoplist="list-v1",
        trainer=SetFitModelTrainer(),
        store=LocalModelStore(tmp_path),
        config=TrainingConfig(encoder=ENCODER, seed=42, num_iterations=4, batch_size=8),
        threshold=0.5,
        now=lambda: datetime(2026, 10, 15, tzinfo=UTC),
        timer=time.perf_counter,
    )

    directory = tmp_path / card.name
    assert directory_hash(directory) == card.model_version
    assert card.labels == model_labels(SECTORS)
    assert card.environment["device"]
    assert card.training_seconds > 0
    assert (directory / CARD_FILE).exists()
    assert {p.name for p in Path.cwd().iterdir()} == cwd_before  # no ./checkpoints left behind
    predictor = SetFitPredictor.load(directory)
    assert list(predictor.probabilities("El hospital amplía la plantilla")) == list(card.labels)


def test_the_learning_curve_trains_and_scores_with_the_real_trainer() -> None:
    """Two folds of six, one size: the real model predicts one probability per label and text."""
    from datos.classification.application.learning_curve import (
        CurvePoint,
        CurveSettings,
        plan_curve,
        run_curve,
    )
    from datos.classification.application.store_classifications import ArticleText
    from datos.classification.application.train_model import TrainingConfig, TrainingSetInfo
    from datos.classification.domain.training_set import LabelledExample
    from datos.classification.infrastructure.setfit_trainer import SetFitModelTrainer
    from datos.governments.application.published import CompetenceLevel

    sector_of = {0: "education", 1: "health", 2: "housing"}
    level_of = {1: CompetenceLevel.CCAA, 3: CompetenceLevel.STATE}
    examples = [
        LabelledExample(i, frozenset({sector_of[s]}), frozenset({level_of[lv]}), "random", False)
        for i, (_, s, lv) in enumerate(EXAMPLES, start=1)
    ]
    articles = {i: ArticleText(i, text, None) for i, (text, _, _) in enumerate(EXAMPLES, start=1)}

    class Texts:
        def texts(self, article_ids: Collection[int]) -> dict[int, ArticleText]:
            return {i: articles[i] for i in article_ids}

    class Store:
        def __init__(self) -> None:
            self.stored: list[CurvePoint] = []

        def points(self) -> list[CurvePoint]:
            return list(self.stored)

        def add(self, point: CurvePoint) -> None:
            self.stored.append(point)

    settings = CurveSettings(
        training_set=TrainingSetInfo("toy-set", "0123456789ab"),
        config=TrainingConfig(encoder=ENCODER, seed=42, num_iterations=4, batch_size=8),
        folds=2,
        threshold=0.5,
        tag_stoplist="list-v1",
    )
    store = Store()
    plan = plan_curve(
        examples=examples,
        settings=settings,
        run_folds=(0, 1),
        sizes=(6,),
        sector_ids=SECTORS,
        test_ids=set(),
        texts=Texts(),
        store=store,
    )
    points = run_curve(
        plan,
        trainer=SetFitModelTrainer(),
        store=store,
        settings=settings,
        timer=time.perf_counter,
        on_point=lambda _: None,
    )

    assert [(p.fold, p.size) for p in points] == [(0, 6), (1, 6)]
    assert all({s.family for s in p.scores} == {"sector", "level"} for p in points)
    assert all(p.training_seconds > 0 for p in points)


def test_the_evaluation_runs_with_a_real_trained_model(tmp_path: Path) -> None:
    """Train a tiny model, wrap it as the classifier production uses, and evaluate it."""
    from datetime import UTC, datetime

    from datos.classification.application.evaluate_model import evaluate_model
    from datos.classification.application.store_classifications import ArticleText
    from datos.classification.application.train_model import (
        TrainingConfig,
        TrainingSetInfo,
        train_model,
    )
    from datos.classification.domain.labels import Labels
    from datos.classification.domain.training_set import LabelledExample
    from datos.classification.infrastructure.local_model_store import LocalModelStore
    from datos.classification.infrastructure.setfit_trainer import SetFitModelTrainer
    from datos.governments.application.published import CompetenceLevel

    sector_of = {0: "education", 1: "health", 2: "housing"}
    level_of = {1: CompetenceLevel.CCAA, 3: CompetenceLevel.STATE}
    examples = [
        LabelledExample(i, frozenset({sector_of[s]}), frozenset({level_of[lv]}), "random", False)
        for i, (_, s, lv) in enumerate(EXAMPLES, start=1)
    ]
    articles = {i: ArticleText(i, text, None) for i, (text, _, _) in enumerate(EXAMPLES, start=1)}

    class Texts:
        def texts(self, article_ids: Collection[int]) -> dict[int, ArticleText]:
            return {i: articles[i] for i in article_ids}

    class Outlets:
        def outlets(self, article_ids: Collection[int]) -> dict[int, str]:
            return {i: f"outlet-{i % 3}" for i in article_ids}

    class NoRules:
        model_id = "rules"
        model_version = "none"

        def classify(self, headline: str, lead: str | None, tags: Sequence[str] = ()) -> Labels:
            return Labels(frozenset(), frozenset(), frozenset())

    card = train_model(
        examples=examples,
        training_set=TrainingSetInfo("toy-set", "0123456789ab"),
        sector_ids=SECTORS,
        test_ids=set(),
        texts=Texts(),
        tag_stoplist="list-v1",
        trainer=SetFitModelTrainer(),
        store=LocalModelStore(tmp_path),
        config=TrainingConfig(encoder=ENCODER, seed=42, num_iterations=4, batch_size=8),
        threshold=0.5,
        now=lambda: datetime(2026, 10, 15, tzinfo=UTC),
        timer=time.perf_counter,
    )
    model = SetFitClassifier(
        SetFitPredictor.load(tmp_path / card.name),
        model_version=card.model_version,
        sector_ids=SECTORS,
    )

    sector, level = evaluate_model(
        examples,  # the training set itself: only the wiring is tested, not the model
        sector_ids=SECTORS,
        texts=Texts(),
        outlets=Outlets(),
        rules=NoRules(),
        candidate=model,
        seed=1,
    )

    assert (sector.family, level.family) == ("sector", "level")
    assert sector.gain.candidate_macro_f1 is not None
    assert len(sector.outlets.outlets) == 3
