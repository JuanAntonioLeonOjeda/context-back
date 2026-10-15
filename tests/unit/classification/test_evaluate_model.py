"""The evaluation use case with fake classifiers: what each sees, compares and misses."""

from collections.abc import Collection, Mapping

import pytest

from datos.classification.application.evaluate_model import evaluate_model, evaluated_articles
from datos.classification.application.store_classifications import ArticleText
from datos.classification.domain.labels import Labels
from datos.classification.domain.training_set import LabelledExample, TrainingSetError
from datos.governments.application.published import CompetenceLevel

CCAA = CompetenceLevel.CCAA
SECTORS = {"education", "health", "housing"}


class Texts:
    def texts(self, article_ids: Collection[int]) -> Mapping[int, ArticleText]:
        return {i: ArticleText(i, f"titular {i}", None) for i in article_ids if i != 99}


class Outlets:
    def outlets(self, article_ids: Collection[int]) -> Mapping[int, str]:
        return {i: "outlet-a" if i % 2 else "outlet-b" for i in article_ids}


class Fixed:
    """Gives the same labels to every article and records what it was shown."""

    def __init__(self, model_id: str, labels: Labels) -> None:
        self.model_id = model_id
        self.model_version = "v1"
        self._labels = labels
        self.seen: list[tuple[str, str | None]] = []

    def classify(self, headline: str, lead: str | None) -> Labels:
        self.seen.append((headline, lead))
        return self._labels


def labels(sectors: set[str], levels: set[CompetenceLevel]) -> Labels:
    return Labels(frozenset({"ccaa-05"}), frozenset(sectors), frozenset(levels))


def example(article_id: int, stratum: str = "random") -> LabelledExample:
    return LabelledExample(article_id, frozenset({"health"}), frozenset({CCAA}), stratum, False)


def test_each_article_gets_gold_rules_and_candidate_labels_without_communities() -> None:
    rules = Fixed("rules", labels(set(), {CCAA}))
    model = Fixed("setfit", labels({"health"}, {CCAA}))

    [first, second] = evaluated_articles(
        [example(2), example(1, "enriched")],
        texts=Texts(),
        outlets=Outlets(),
        rules=rules,
        candidate=model,
    )

    assert (first.article_id, first.outlet_id, first.stratum) == (1, "outlet-a", "enriched")
    assert second.outlet_id == "outlet-b"
    assert first.gold == {"sector:health", "level:ccaa"}
    assert first.rules == {"level:ccaa"}
    assert first.candidate == {"sector:health", "level:ccaa"}


def test_classifiers_see_headline_and_lead_only() -> None:
    rules = Fixed("rules", labels(set(), set()))
    model = Fixed("setfit", labels(set(), set()))

    evaluated_articles([example(3)], texts=Texts(), outlets=Outlets(), rules=rules, candidate=model)

    assert rules.seen == model.seen == [("titular 3", None)]


def test_an_article_missing_from_the_database_stops_the_evaluation() -> None:
    with pytest.raises(TrainingSetError, match=r"not in the database: \[99\]"):
        evaluated_articles(
            [example(1), example(99)],
            texts=Texts(),
            outlets=Outlets(),
            rules=Fixed("rules", labels(set(), set())),
            candidate=Fixed("setfit", labels(set(), set())),
        )


def test_a_model_that_finds_the_sector_the_rules_miss_is_promoted_for_sectors_only() -> None:
    family_verdicts = evaluate_model(
        [example(i) for i in range(1, 9)],
        sector_ids=SECTORS,
        texts=Texts(),
        outlets=Outlets(),
        rules=Fixed("rules", labels(set(), {CCAA})),
        candidate=Fixed("setfit", labels({"health"}, {CCAA})),
        seed=1,
    )

    sector, level = family_verdicts
    assert (sector.family, sector.promoted) == ("sector", True)
    assert (level.family, level.promoted) == ("level", False)  # equal: no gain
