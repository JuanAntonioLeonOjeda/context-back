"""The curve's results file: points survive a round trip and a broken line is never skipped."""

from pathlib import Path

import pytest

from datos.classification.application.learning_curve import CurvePoint
from datos.classification.domain.metrics import FamilyScore, LabelScore
from datos.classification.domain.training_set import TrainingSetError
from datos.classification.infrastructure.curve_file import JsonlCurveStore


def a_point(fold: int = 0, size: int = 100, macro: float | None = 0.5) -> CurvePoint:
    sector = FamilyScore("sector", macro, (LabelScore("sector:health", 3, 2, macro),))
    level = FamilyScore("level", None, (LabelScore("level:local", 0, 0, None),))
    settings = {"folds": 4, "threshold": 0.5, "training": {"seed": 42, "num_iterations": None}}
    return CurvePoint(fold, size, (sector, level), 12.5, settings)


def test_a_missing_file_has_no_points(tmp_path: Path) -> None:
    assert JsonlCurveStore(tmp_path / "curve.jsonl").points() == []


def test_points_come_back_as_they_were_written_in_order(tmp_path: Path) -> None:
    store = JsonlCurveStore(tmp_path / "out" / "curve.jsonl")
    points = [a_point(0, 100), a_point(0, 200, macro=None), a_point(1, 100)]

    for point in points:
        store.add(point)

    assert list(JsonlCurveStore(tmp_path / "out" / "curve.jsonl").points()) == points


def test_each_point_is_one_line_added_to_the_file(tmp_path: Path) -> None:
    path = tmp_path / "curve.jsonl"
    store = JsonlCurveStore(path)

    store.add(a_point(0, 100))
    store.add(a_point(0, 200))

    assert len(path.read_text(encoding="utf-8").splitlines()) == 2


def test_a_line_that_cannot_be_read_stops_with_its_line_number(tmp_path: Path) -> None:
    path = tmp_path / "curve.jsonl"
    store = JsonlCurveStore(path)
    store.add(a_point())
    with path.open("a", encoding="utf-8") as file:
        file.write('{"fold": 0, "size"\n')  # a write cut in the middle

    with pytest.raises(TrainingSetError, match=r"curve\.jsonl line 2"):
        store.points()
