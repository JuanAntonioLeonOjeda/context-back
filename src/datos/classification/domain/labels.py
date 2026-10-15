"""What a classifier says about an article (the labels of docs/labelling-guide.md)."""

from dataclasses import dataclass

from datos.governments.application.published import CompetenceLevel


@dataclass(frozen=True, slots=True)
class Evidence:
    """A piece of the text that produced a label, so every label can be explained."""

    term: str
    gives: str  # "community:ccaa-05", "level:ccaa", "sector:health"


@dataclass(frozen=True, slots=True)
class Score:
    """How sure a model is of a label it gives: its probability, between 0 and 1.

    The rules point at a term of the text (`Evidence`); a model has no term to point at, so it says
    how sure it is. The label is named like an evidence entry ("sector:health").
    """

    label: str
    probability: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError(f"probability out of range for {self.label}: {self.probability}")


@dataclass(frozen=True, slots=True)
class Labels:
    communities: frozenset[str]  # territory ids, "ccaa-NN"
    sectors: frozenset[str]  # sector ids
    levels: frozenset[CompetenceLevel]
    evidence: tuple[Evidence, ...] = ()  # what in the text produced each label (the rules)
    scores: tuple[Score, ...] = ()  # how sure a model is of each label it gives


NO_LABELS = Labels(frozenset(), frozenset(), frozenset())
