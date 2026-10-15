"""The composite classifier of ADR-0016: each family of labels from its assigned classifier."""

from pathlib import Path

import pytest

from datos.classification.application.composite_classifier import (
    EVIDENCE_PREFIX,
    CompositeClassifier,
    Family,
)
from datos.classification.domain.labels import Evidence, Labels, Score
from datos.classification.infrastructure.rules_classifier import load_rules_classifier
from datos.governments.application.published import CompetenceLevel

STATE, CCAA = CompetenceLevel.STATE, CompetenceLevel.CCAA


class Fixed:
    """A classifier that always says the same, and counts how often it is asked."""

    def __init__(self, model_id: str, labels: Labels) -> None:
        self.model_id = model_id
        self.model_version = "v1"
        self._labels = labels
        self.calls = 0

    def classify(self, headline: str, lead: str | None) -> Labels:
        self.calls += 1
        return self._labels


RULES = Fixed(
    "rules",
    Labels(
        communities=frozenset({"ccaa-05"}),
        sectors=frozenset({"housing"}),
        levels=frozenset({CCAA}),
        evidence=(
            Evidence("Canarias", "community:ccaa-05"),
            Evidence("vivienda", "sector:housing"),
            Evidence("Gobierno de Canarias", "level:ccaa"),
        ),
    ),
)
MODEL = Fixed(
    "setfit",
    Labels(communities=frozenset(), sectors=frozenset({"health"}), levels=frozenset({STATE})),
)


def test_takes_each_family_from_the_classifier_assigned_to_it() -> None:
    composite = CompositeClassifier(
        {Family.COMMUNITIES: RULES, Family.SECTORS: MODEL, Family.LEVELS: RULES}
    )

    labels = composite.classify("titular", None)

    assert labels.communities == {"ccaa-05"}  # rules
    assert labels.sectors == {"health"}  # model
    assert labels.levels == {CCAA}  # rules


def test_keeps_only_the_evidence_of_the_families_each_source_supplies() -> None:
    composite = CompositeClassifier(
        {Family.COMMUNITIES: RULES, Family.SECTORS: MODEL, Family.LEVELS: RULES}
    )

    gives = [e.gives for e in composite.classify("titular", None).evidence]

    # The rules' sector term is dropped: the sector came from the model.
    assert gives == ["community:ccaa-05", "level:ccaa"]


def test_its_version_names_the_source_of_every_family_in_a_fixed_order() -> None:
    composite = CompositeClassifier(
        {Family.LEVELS: MODEL, Family.SECTORS: MODEL, Family.COMMUNITIES: RULES}
    )

    assert composite.model_id == "composite"
    assert composite.model_version == ("communities=rules@v1;sectors=setfit@v1;levels=setfit@v1")


def test_a_source_that_supplies_two_families_runs_once_per_article() -> None:
    rules = Fixed("rules", RULES.classify("", None))
    model = Fixed("setfit", MODEL.classify("", None))
    composite = CompositeClassifier(
        {Family.COMMUNITIES: rules, Family.SECTORS: model, Family.LEVELS: model}
    )

    composite.classify("titular", "entradilla")

    assert (rules.calls, model.calls) == (1, 1)


def test_refuses_to_be_built_without_a_classifier_for_every_family() -> None:
    with pytest.raises(ValueError, match="levels"):
        CompositeClassifier({Family.COMMUNITIES: RULES, Family.SECTORS: RULES})


def test_every_family_has_an_evidence_prefix() -> None:
    # A family added without one would silently lose its evidence.
    assert set(EVIDENCE_PREFIX) == set(Family)


def test_made_only_of_the_rules_it_says_exactly_what_the_rules_say() -> None:
    rules = load_rules_classifier(
        Path("data/classification"), sector_ids=frozenset({"education", "health", "housing"})
    )
    composite = CompositeClassifier(dict.fromkeys(Family, rules))

    for headline, lead in [
        ("El Gobierno de Canarias aprueba un plan de vivienda", "En Gran Canaria y Tenerife."),
        ("La Xunta y el ministerio chocan por las plazas MIR", None),
        ("Netflix emitirá los partidos del Mundial", ""),
    ]:
        assert composite.classify(headline, lead) == rules.classify(headline, lead)


def test_keeps_only_the_scores_of_the_families_each_source_supplies() -> None:
    model = Fixed(
        "setfit",
        Labels(
            communities=frozenset(),
            sectors=frozenset({"health"}),
            levels=frozenset({STATE}),
            scores=(Score("sector:health", 0.83), Score("level:state", 0.61)),
        ),
    )
    composite = CompositeClassifier(
        {Family.COMMUNITIES: RULES, Family.SECTORS: model, Family.LEVELS: RULES}
    )

    # The model's level score is dropped: the levels came from the rules.
    assert composite.classify("titular", None).scores == (Score("sector:health", 0.83),)


def test_the_rules_give_no_scores_and_the_composite_of_the_rules_neither() -> None:
    composite = CompositeClassifier(dict.fromkeys(Family, RULES))

    assert RULES.classify("titular", None).scores == ()
    assert composite.classify("titular", None).scores == ()
