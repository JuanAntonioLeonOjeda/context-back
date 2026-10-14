"""Use case: classify the articles a classifier version has not seen yet, and store the result.

Idempotent: an article is classified once per (model id, version), so running it again after a
collection touches only the new articles, and running it after the rules changed (a new
version) classifies everything again alongside the old rows, which stay for comparison.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import structlog

from datos.classification.application.classifier import ArticleClassifier
from datos.classification.domain.labels import Labels

log = structlog.get_logger(__name__)

BATCH_SIZE = 500


@dataclass(frozen=True, slots=True)
class ArticleText:
    """What a classifier may see of an article: never the outlet (ADR-0015)."""

    article_id: int
    headline: str
    lead: str | None


class ClassificationRepository(Protocol):
    def unclassified(self, model_id: str, model_version: str, *, limit: int) -> list[ArticleText]:
        """Articles with no classification of this classifier version, oldest first."""
        ...

    def add(self, model_id: str, model_version: str, results: Sequence[tuple[int, Labels]]) -> int:
        """Store the results append-only; return how many rows were new."""
        ...


def classify_new(classifier: ArticleClassifier, repository: ClassificationRepository) -> int:
    """Classify every article this classifier version has not seen; return how many were stored."""
    stored = 0
    while True:
        batch = repository.unclassified(
            classifier.model_id, classifier.model_version, limit=BATCH_SIZE
        )
        if not batch:
            break
        results = [(a.article_id, classifier.classify(a.headline, a.lead)) for a in batch]
        stored += repository.add(classifier.model_id, classifier.model_version, results)
    log.info(
        "classification_finished",
        model_id=classifier.model_id,
        model_version=classifier.model_version,
        stored=stored,
    )
    return stored
