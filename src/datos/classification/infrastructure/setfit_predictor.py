"""The real predictor of the own model (ADR-0016): the only code that imports SetFit.

It needs the `ml` dependency group (`uv sync --group ml`), which is never in the API image. SetFit
is imported inside `load`, so importing this module costs nothing and loads no torch.
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol


class ProbabilityModel(Protocol):
    """What the predictor needs of a trained SetFit model; a fake in the unit tests."""

    labels: list[str] | None

    def predict_proba(self, inputs: str, *, as_numpy: bool = False) -> Any:  # noqa: ANN401 - torch or numpy
        ...


class SetFitPredictor:
    def __init__(self, model: ProbabilityModel) -> None:
        if not model.labels:
            raise ValueError("the model has no label names: it was not trained for this project")
        self._model = model
        self._labels = list(model.labels)

    @classmethod
    def load(cls, directory: Path) -> "SetFitPredictor":
        """A model saved by the training job: the weights and the label names in one directory."""
        from setfit import SetFitModel  # lazy on purpose, see the module docstring

        # Typed through a Protocol: SetFit ships no type information.
        model: ProbabilityModel = SetFitModel.from_pretrained(str(directory))
        return cls(model)

    def probabilities(self, text: str) -> Mapping[str, float]:
        values = self._model.predict_proba(text, as_numpy=True)
        # strict: a model that gives a different number of probabilities than it has labels is
        # broken, and zipping the shorter would silently drop a label.
        return {
            label: float(probability)
            for label, probability in zip(self._labels, values, strict=True)
        }
