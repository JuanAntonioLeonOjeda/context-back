"""The predictor's own logic, with a fake model: no torch, no network."""

import pytest

from datos.classification.infrastructure.setfit_predictor import SetFitPredictor


class FakeModel:
    def __init__(self, labels: list[str] | None, values: list[float]) -> None:
        self.labels = labels
        self._values = values
        self.asked: list[tuple[str, bool]] = []

    def predict_proba(self, inputs: str, *, as_numpy: bool = False) -> list[float]:
        self.asked.append((inputs, as_numpy))
        return self._values


def test_pairs_each_label_with_its_probability_in_the_models_order() -> None:
    model = FakeModel(["sector:health", "level:state"], [0.83, 0.61])

    assert SetFitPredictor(model).probabilities("titular") == {
        "sector:health": 0.83,
        "level:state": 0.61,
    }


def test_asks_the_model_for_numbers_not_tensors() -> None:
    model = FakeModel(["sector:health"], [0.5])

    SetFitPredictor(model).probabilities("titular")

    assert model.asked == [("titular", True)]


def test_a_model_without_label_names_is_refused_at_load() -> None:
    no_names: list[list[str] | None] = [None, []]
    for labels in no_names:
        with pytest.raises(ValueError, match="label names"):
            SetFitPredictor(FakeModel(labels, []))


def test_a_model_that_gives_a_different_number_of_probabilities_than_labels_fails() -> None:
    too_few = FakeModel(["sector:health", "level:state"], [0.9])
    too_many = FakeModel(["sector:health"], [0.9, 0.1])

    for model in (too_few, too_many):
        with pytest.raises(ValueError, match="zip"):
            SetFitPredictor(model).probabilities("titular")
