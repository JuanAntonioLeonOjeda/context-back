"""The learning curve's results, one JSON line per measured point (ADR-0016).

Append-only: a point is written as soon as it is measured, so a run that is cut loses only the point
in progress and the next run carries on from the file. A line that cannot be read stops the run
with its line number instead of being skipped: skipping would train that point again without anyone
noticing.
"""

import json
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, ValidationError

from datos.classification.application.learning_curve import CurvePoint
from datos.classification.domain.metrics import FamilyScore, LabelScore
from datos.classification.domain.training_set import TrainingSetError


class _LabelScoreLine(BaseModel):
    label: str
    support: int
    predicted: int
    f1: float | None


class _FamilyScoreLine(BaseModel):
    family: str
    macro_f1: float | None
    labels: list[_LabelScoreLine]


class _PointLine(BaseModel):
    fold: int
    size: int
    scores: list[_FamilyScoreLine]
    training_seconds: float
    settings: dict[str, object]


class JsonlCurveStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def points(self) -> Sequence[CurvePoint]:
        if not self._path.exists():
            return []
        points: list[CurvePoint] = []
        for number, line in enumerate(self._path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                points.append(_to_point(_PointLine.model_validate_json(line)))
            except ValidationError as error:
                raise TrainingSetError(f"{self._path.name} line {number}: {error}") from error
        return points

    def add(self, point: CurvePoint) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(_to_dict(point), ensure_ascii=False, sort_keys=True) + "\n"
        with self._path.open("a", encoding="utf-8") as file:
            file.write(line)  # one write of a whole line: a cut leaves no half-written point


def _to_dict(point: CurvePoint) -> dict[str, object]:
    return {
        "fold": point.fold,
        "size": point.size,
        "scores": [
            {
                "family": s.family,
                "macro_f1": s.macro_f1,
                "labels": [
                    {"label": b.label, "support": b.support, "predicted": b.predicted, "f1": b.f1}
                    for b in s.labels
                ],
            }
            for s in point.scores
        ],
        "training_seconds": point.training_seconds,
        "settings": dict(point.settings),
    }


def _to_point(line: _PointLine) -> CurvePoint:
    return CurvePoint(
        fold=line.fold,
        size=line.size,
        scores=tuple(
            FamilyScore(
                s.family,
                s.macro_f1,
                tuple(LabelScore(b.label, b.support, b.predicted, b.f1) for b in s.labels),
            )
            for s in line.scores
        ),
        training_seconds=line.training_seconds,
        settings=line.settings,
    )
