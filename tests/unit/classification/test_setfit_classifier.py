"""The adapter of the own model, with a fake predictor: no network, no GPU."""

from collections.abc import Mapping

import pytest

from datos.classification.domain.labels import NO_LABELS, Score
from datos.classification.infrastructure.setfit_classifier import SetFitClassifier
from datos.governments.application.published import CompetenceLevel

SECTORS = frozenset({"education", "health", "housing"})
CCAA, STATE = CompetenceLevel.CCAA, CompetenceLevel.STATE


class FakePredictor:
    """Says the same probabilities for every text, and remembers what it was asked."""

    def __init__(self, probabilities: Mapping[str, float]) -> None:
        self._probabilities = dict(probabilities)
        self.asked: list[str] = []

    def probabilities(self, text: str) -> Mapping[str, float]:
        self.asked.append(text)
        return self._probabilities


def classifier(probabilities: Mapping[str, float], **options: float) -> SetFitClassifier:
    return SetFitClassifier(
        FakePredictor(probabilities), model_version="w1", sector_ids=SECTORS, **options
    )


ALL = {
    "sector:education": 0.10,
    "sector:health": 0.83,
    "sector:housing": 0.50,
    "level:state": 0.61,
    "level:ccaa": 0.49,
    "level:local": 0.02,
}


def test_assigns_the_labels_at_or_above_the_threshold() -> None:
    labels = classifier(ALL).classify("titular", None)

    assert labels.sectors == {"health", "housing"}  # 0.50 is at the threshold: in
    assert labels.levels == {STATE}  # 0.49 is below it: out


def test_the_scores_are_those_of_the_labels_it_gives_in_a_fixed_order() -> None:
    labels = classifier(ALL).classify("titular", None)

    assert labels.scores == (
        Score("level:state", 0.61),
        Score("sector:health", 0.83),
        Score("sector:housing", 0.50),
    )


def test_never_gives_communities_or_evidence() -> None:
    labels = classifier(ALL).classify("titular", None)

    assert labels.communities == frozenset()
    assert labels.evidence == ()


def test_the_threshold_can_be_changed_but_only_to_a_sensible_value() -> None:
    assert classifier(ALL, threshold=0.9).classify("t", None).sectors == frozenset()
    assert classifier(ALL, threshold=0.05).classify("t", None).sectors == SECTORS
    for bad in (0.0, -0.1, 1.5):
        with pytest.raises(ValueError, match="threshold"):
            classifier(ALL, threshold=bad)


def test_reads_the_headline_and_the_lead_together() -> None:
    predictor = FakePredictor(ALL)
    model = SetFitClassifier(predictor, model_version="w1", sector_ids=SECTORS)

    model.classify("El Gobierno amplía la plantilla", "En los hospitales públicos.")
    model.classify("Solo titular", None)

    assert predictor.asked == [
        "El Gobierno amplía la plantilla En los hospitales públicos.",
        "Solo titular",
    ]


def test_a_text_with_nothing_in_it_has_no_labels_and_the_predictor_is_not_asked() -> None:
    predictor = FakePredictor(ALL)
    model = SetFitClassifier(predictor, model_version="w1", sector_ids=SECTORS)

    assert model.classify("", None) == NO_LABELS
    assert model.classify("  ", "") == NO_LABELS
    assert predictor.asked == []


@pytest.mark.parametrize(
    "label", ["community:ccaa-05", "sector:transport", "level:county", "party:pp", "health"]
)
def test_a_label_outside_the_vocabulary_fails_loudly_even_below_the_threshold(label: str) -> None:
    with pytest.raises(ValueError, match="does not know"):
        classifier({"sector:health": 0.9, label: 0.01}).classify("titular", None)


def test_identifies_itself_and_needs_a_version() -> None:
    model = classifier(ALL)

    assert (model.model_id, model.model_version) == ("setfit", "w1")
    with pytest.raises(ValueError, match="version"):
        SetFitClassifier(FakePredictor(ALL), model_version="", sector_ids=SECTORS)


def test_the_same_text_gets_the_same_labels() -> None:
    model = classifier(ALL)

    assert model.classify("titular", "entradilla") == model.classify("titular", "entradilla")
