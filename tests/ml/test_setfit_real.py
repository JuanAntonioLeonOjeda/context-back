"""The own model with SetFit itself (ADR-0016): `uv run pytest -m ml`.

Needs the `ml` group and downloads the encoder the first time (about 1.2 GB into the Hugging Face
cache). It trains a tiny model on made-up headlines, so it checks that the pieces fit (training,
saving, loading, the labels surviving, the adapter reading it), not that the model is any good: that
is the evaluation of task 18, on the blind test set. Never runs in CI.
"""

import time
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
