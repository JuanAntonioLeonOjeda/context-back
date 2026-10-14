"""What a classifier says about an article (the labels of docs/labelling-guide.md)."""

from dataclasses import dataclass

from datos.governments.application.published import CompetenceLevel


@dataclass(frozen=True, slots=True)
class Evidence:
    """A piece of the text that produced a label, so every label can be explained."""

    term: str
    gives: str  # "community:ccaa-05", "level:ccaa", "sector:health"


@dataclass(frozen=True, slots=True)
class Labels:
    communities: frozenset[str]  # territory ids, "ccaa-NN"
    sectors: frozenset[str]  # sector ids
    levels: frozenset[CompetenceLevel]
    evidence: tuple[Evidence, ...] = ()


NO_LABELS = Labels(frozenset(), frozenset(), frozenset())
