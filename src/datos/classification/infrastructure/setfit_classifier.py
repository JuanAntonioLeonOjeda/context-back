"""The own model as an ArticleClassifier (ADR-0016): sectors and government levels.

It asks a `ProbabilityPredictor` how likely each label is, assigns the ones at or above the
threshold and keeps their probability as a score. It never gives communities (they stay with the
rules) and never sees the outlet. The version is given by the caller: a hash of the weights file.
"""

from collections.abc import Collection

from datos.classification.application.probability_predictor import ProbabilityPredictor
from datos.classification.domain.labels import NO_LABELS, Labels, Score
from datos.classification.domain.text import article_text
from datos.governments.application.published import CompetenceLevel

DEFAULT_THRESHOLD = 0.5  # fixed and written in the model's metadata; never tuned on the test set
_SECTOR = "sector:"
_LEVEL = "level:"


class SetFitClassifier:
    model_id = "setfit"

    def __init__(
        self,
        predictor: ProbabilityPredictor,
        *,
        model_version: str,
        sector_ids: Collection[str],
        threshold: float = DEFAULT_THRESHOLD,
    ) -> None:
        if not 0.0 < threshold <= 1.0:
            raise ValueError(f"threshold must be in (0, 1]: {threshold}")
        if not model_version:
            raise ValueError("a model needs a version")
        self._predictor = predictor
        self._sector_ids = frozenset(sector_ids)
        self._levels = frozenset(level.value for level in CompetenceLevel)
        self._threshold = threshold
        self.model_version = model_version

    def classify(self, headline: str, lead: str | None) -> Labels:
        text = article_text(headline, lead)
        if not text:
            return NO_LABELS  # nothing to read: the predictor is not asked
        probabilities = self._predictor.probabilities(text)
        for label in probabilities:
            self._check(label)
        given = sorted(label for label, p in probabilities.items() if p >= self._threshold)
        return Labels(
            communities=frozenset(),
            sectors=frozenset(
                label.removeprefix(_SECTOR) for label in given if _is(label, _SECTOR)
            ),
            levels=frozenset(
                CompetenceLevel(label.removeprefix(_LEVEL)) for label in given if _is(label, _LEVEL)
            ),
            scores=tuple(Score(label, probabilities[label]) for label in given),
        )

    def _check(self, label: str) -> None:
        """A label outside the project's vocabulary fails loudly: never ignored, never guessed."""
        if _is(label, _SECTOR) and label.removeprefix(_SECTOR) in self._sector_ids:
            return
        if _is(label, _LEVEL) and label.removeprefix(_LEVEL) in self._levels:
            return
        raise ValueError(f"the model gave a label the project does not know: {label}")


def _is(label: str, prefix: str) -> bool:
    return label.startswith(prefix)
