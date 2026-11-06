from collections.abc import Sequence

from datos.classification.application.store_classifications import ArticleText, classify_new
from datos.classification.domain.labels import NO_LABELS, Labels


class _Classifier:
    model_id = "fake"
    model_version = "v1"

    def __init__(self) -> None:
        self.seen: list[tuple[str, str | None, Sequence[str]]] = []

    def classify(self, headline: str, lead: str | None, tags: Sequence[str] = ()) -> Labels:
        self.seen.append((headline, lead, tags))
        return NO_LABELS


class _Repository:
    def __init__(self, articles: list[ArticleText]) -> None:
        self._pending = articles
        self.stored: list[int] = []

    def unclassified(self, model_id: str, model_version: str, *, limit: int) -> list[ArticleText]:
        batch, self._pending = self._pending[:limit], self._pending[limit:]
        return batch

    def add(self, model_id: str, model_version: str, results: Sequence[tuple[int, Labels]]) -> int:
        self.stored += [article_id for article_id, _ in results]
        return len(results)


def test_every_article_is_classified_with_its_tags() -> None:
    classifier = _Classifier()
    repository = _Repository(
        [
            ArticleText(1, "Titular", "Entradilla.", ("Sanidad", "Madrid")),
            ArticleText(2, "Otro titular", None),
        ]
    )

    stored = classify_new(classifier, repository)

    assert stored == 2 and repository.stored == [1, 2]
    assert classifier.seen == [
        ("Titular", "Entradilla.", ("Sanidad", "Madrid")),
        ("Otro titular", None, ()),
    ]
