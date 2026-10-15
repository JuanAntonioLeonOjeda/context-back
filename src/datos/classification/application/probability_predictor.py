"""The one thing the own model must do: say how likely each label is for a text (ADR-0016).

A port, so the classifier that applies the threshold and speaks the project's vocabulary can be
tested without the model (no network, no GPU). The real predictor, on SetFit, lives in
infrastructure and is the only code that imports it.
"""

from collections.abc import Mapping
from typing import Protocol


class ProbabilityPredictor(Protocol):
    def probabilities(self, text: str) -> Mapping[str, float]:
        """The probability, between 0 and 1, of each label the model knows, for `text`.

        Labels are named like an evidence entry: "sector:health", "level:ccaa". The same labels
        for every text: a model that sometimes leaves one out is not a model of that label.
        """
        ...
