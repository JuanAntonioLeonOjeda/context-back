"""Use case: evaluate the own model against the rules on the blind test set (task 18, ADR-0016).

Both classifiers read each test-set article from its headline and lead, as they do in production,
and nothing is stored: the evaluation labels in memory and returns the verdicts. The outlet of
each article is read apart, only to count the per-outlet criterion; no classifier sees it.
"""

from collections.abc import Collection, Mapping, Sequence
from typing import Protocol

from datos.classification.application.classifier import ArticleClassifier
from datos.classification.application.train_model import ArticleTextReader
from datos.classification.domain.labels import Labels
from datos.classification.domain.promotion import EvaluatedArticle, FamilyVerdict, verdicts
from datos.classification.domain.training_set import LabelledExample, TrainingSetError, model_labels


class ArticleOutletReader(Protocol):
    def outlets(self, article_ids: Collection[int]) -> Mapping[int, str]:
        """article id → outlet id, for the articles that exist."""
        ...


def evaluated_articles(
    examples: Sequence[LabelledExample],
    *,
    texts: ArticleTextReader,
    outlets: ArticleOutletReader,
    rules: ArticleClassifier,
    candidate: ArticleClassifier,
) -> list[EvaluatedArticle]:
    """Every test-set article with its gold labels and those of both classifiers, by id."""
    ids = sorted(e.article_id for e in examples)
    found_texts = texts.texts(ids)
    found_outlets = outlets.outlets(ids)
    missing = [i for i in ids if i not in found_texts or i not in found_outlets]
    if missing:
        raise TrainingSetError(f"test-set articles not in the database: {missing[:5]}")
    by_id = {e.article_id: e for e in examples}
    evaluated: list[EvaluatedArticle] = []
    for article_id in ids:
        text = found_texts[article_id]
        example = by_id[article_id]
        evaluated.append(
            EvaluatedArticle(
                article_id=article_id,
                outlet_id=found_outlets[article_id],
                stratum=example.stratum,
                gold=frozenset(
                    {f"sector:{s}" for s in example.sectors}
                    | {f"level:{lv.value}" for lv in example.levels}
                ),
                rules=_label_set(rules.classify(text.headline, text.lead, text.tags)),
                candidate=_label_set(candidate.classify(text.headline, text.lead, text.tags)),
            )
        )
    return evaluated


def evaluate_model(
    examples: Sequence[LabelledExample],
    *,
    sector_ids: Collection[str],
    texts: ArticleTextReader,
    outlets: ArticleOutletReader,
    rules: ArticleClassifier,
    candidate: ArticleClassifier,
    seed: int,
) -> tuple[FamilyVerdict, ...]:
    articles = evaluated_articles(
        examples, texts=texts, outlets=outlets, rules=rules, candidate=candidate
    )
    return verdicts(articles, model_labels(sector_ids), seed=seed)


def _label_set(labels: Labels) -> frozenset[str]:
    """The families the model may take over, in the model's vocabulary; communities left out."""
    return frozenset(
        {f"sector:{s}" for s in labels.sectors} | {f"level:{lv.value}" for lv in labels.levels}
    )
