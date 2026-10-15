"""The contract of the ArticleClassifier port (ADR-0015). Every adapter runs this same suite:
the rules now, the own model when it exists."""

import csv
import inspect
from pathlib import Path

import pytest

from datos.classification.application.classifier import ArticleClassifier
from datos.classification.application.composite_classifier import CompositeClassifier, Family
from datos.classification.infrastructure.rules_classifier import load_rules_classifier
from datos.classification.infrastructure.setfit_classifier import SetFitClassifier
from datos.governments.application.published import CompetenceLevel


def _rows(path: str) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


SECTORS = frozenset(r["id"] for r in _rows("data/governments/sectors.csv"))
COMMUNITIES = frozenset(
    r["id"] for r in _rows("data/territories/territories.csv") if r["level"] == "ccaa"
)
TEXTS = [
    ("La Xunta y el ministerio chocan por las plazas MIR", None),
    ("El Cabildo de Lanzarote construye 200 viviendas públicas", "Las obras empiezan en enero."),
    ("Netflix emitirá los 104 partidos del Mundial 2030", ""),
    ("", None),
]


class _FakePredictor:
    """Deterministic: health when the text speaks of a hospital, the state level for a ministry."""

    def probabilities(self, text: str) -> dict[str, float]:
        lowered = text.lower()
        return {
            "sector:education": 0.05,
            "sector:health": 0.9 if "hospital" in lowered else 0.1,
            "sector:housing": 0.9 if "viviendas" in lowered else 0.1,
            "level:state": 0.9 if "ministerio" in lowered else 0.1,
            "level:ccaa": 0.9 if "xunta" in lowered else 0.1,
            "level:local": 0.9 if "cabildo" in lowered else 0.1,
        }


def adapters() -> list[ArticleClassifier]:
    rules = load_rules_classifier(Path("data/classification"), sector_ids=SECTORS)
    model = SetFitClassifier(_FakePredictor(), model_version="w1", sector_ids=SECTORS)
    mixed = CompositeClassifier(
        {Family.COMMUNITIES: rules, Family.SECTORS: model, Family.LEVELS: model}
    )
    return [rules, CompositeClassifier(dict.fromkeys(Family, rules)), model, mixed]


@pytest.fixture(params=adapters(), ids=lambda c: c.model_id)
def classifier(request: pytest.FixtureRequest) -> ArticleClassifier:
    adapter: ArticleClassifier = request.param
    return adapter


def test_identifies_itself_with_an_id_and_a_version(classifier: ArticleClassifier) -> None:
    assert classifier.model_id and classifier.model_version


def test_labels_use_only_the_project_vocabulary(classifier: ArticleClassifier) -> None:
    for headline, lead in TEXTS:
        labels = classifier.classify(headline, lead)
        assert labels.communities <= COMMUNITIES
        assert labels.sectors <= SECTORS
        assert all(isinstance(level, CompetenceLevel) for level in labels.levels)


def test_is_deterministic(classifier: ArticleClassifier) -> None:
    for headline, lead in TEXTS:
        assert classifier.classify(headline, lead) == classifier.classify(headline, lead)


def test_never_takes_the_outlet_as_an_input(classifier: ArticleClassifier) -> None:
    # Neutrality: the same text gets the same labels whoever published it.
    assert list(inspect.signature(classifier.classify).parameters) == ["headline", "lead"]


def test_every_evidence_term_is_in_the_text(classifier: ArticleClassifier) -> None:
    for headline, lead in TEXTS:
        text = f"{headline} {lead or ''}".lower()
        for evidence in classifier.classify(headline, lead).evidence:
            assert evidence.term.lower() in text


def test_every_score_is_for_a_label_the_classifier_gave(classifier: ArticleClassifier) -> None:
    for headline, lead in TEXTS:
        labels = classifier.classify(headline, lead)
        given = (
            {f"community:{c}" for c in labels.communities}
            | {f"sector:{s}" for s in labels.sectors}
            | {f"level:{level.value}" for level in labels.levels}
        )
        assert {score.label for score in labels.scores} <= given
