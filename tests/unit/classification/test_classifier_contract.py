"""The contract of the ArticleClassifier port (ADR-0015). Every adapter runs this same suite:
the rules now, the own model when it exists."""

import csv
import inspect
from pathlib import Path

import pytest

from datos.classification.application.classifier import ArticleClassifier
from datos.classification.application.composite_classifier import CompositeClassifier, Family
from datos.classification.infrastructure.rules_classifier import load_rules_classifier
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


def adapters() -> list[ArticleClassifier]:
    rules = load_rules_classifier(Path("data/classification"), sector_ids=SECTORS)
    return [rules, CompositeClassifier(dict.fromkeys(Family, rules))]


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
