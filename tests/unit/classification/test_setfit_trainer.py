"""The trained model's probabilities, with a fake in place of SetFit: shape checked, order kept."""

from collections.abc import Sequence

import pytest

from datos.classification.infrastructure.setfit_trainer import TrainedSetFit

LABELS = ["sector:health", "level:state"]


class FakeSetFit:
    def __init__(self, rows: list[list[float]]) -> None:
        self.rows = rows
        self.calls = 0

    def predict_proba(self, inputs: Sequence[str], *, as_numpy: bool = False) -> list[list[float]]:
        self.calls += 1
        return self.rows


def trained(rows: list[list[float]]) -> TrainedSetFit:
    return TrainedSetFit(FakeSetFit(rows), LABELS, {"device": "cpu"})


def test_gives_one_row_per_text_with_one_probability_per_label() -> None:
    assert trained([[0.9, 0.1], [0.2, 0.7]]).predict_proba(["a", "b"]) == [[0.9, 0.1], [0.2, 0.7]]


def test_refuses_a_row_with_fewer_probabilities_than_labels() -> None:
    with pytest.raises(ValueError, match="1 rows of 2 probabilities"):
        trained([[0.9]]).predict_proba(["a"])


def test_refuses_fewer_rows_than_texts() -> None:
    with pytest.raises(ValueError, match="2 rows"):
        trained([[0.9, 0.1]]).predict_proba(["a", "b"])


def test_no_texts_asks_the_model_nothing() -> None:
    fake = FakeSetFit([])

    assert TrainedSetFit(fake, LABELS, {}).predict_proba([]) == []
    assert fake.calls == 0
