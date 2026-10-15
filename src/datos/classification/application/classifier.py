"""The port every classifier implements (ADR-0015): the rules now, the own model later."""

from typing import Protocol

from datos.classification.domain.labels import Labels


class ArticleClassifier(Protocol):
    """Labels an article from its headline and lead only: never its outlet.

    `model_id` and `model_version` are stored with every result, so a label can always be
    traced to what produced it; a change in the classifier changes its version.
    """

    @property
    def model_id(self) -> str: ...

    @property
    def model_version(self) -> str: ...

    def classify(self, headline: str, lead: str | None) -> Labels: ...
