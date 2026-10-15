"""How well predicted labels match the author's, per label and per family (ADR-0016).

Pure: the gold and predicted labels of the same articles in, the scores out. A label is scored
one-vs-rest (each article has it or not), and a family's score is the plain mean of its labels'
F1, so a rare label weighs as much as a common one: that is what macro means. Used by the learning
curve and by the evaluation on the blind test set (task 18), so both measure the same way.
"""

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LabelScore:
    label: str
    support: int  # articles that have the label in the gold labels
    predicted: int  # articles that have it in the predicted labels
    f1: float | None  # None when neither has it: nothing to get right or wrong


@dataclass(frozen=True, slots=True)
class FamilyScore:
    family: str  # "sector" or "level"
    macro_f1: float | None  # mean of the defined F1s; None when no label is defined
    labels: tuple[LabelScore, ...]


def family_of(label: str) -> str:
    """The prefix that `model_labels` gives every label: "sector:health" is a sector."""
    return label.split(":", 1)[0]


def label_score(
    label: str, gold: Sequence[frozenset[str]], predicted: Sequence[frozenset[str]]
) -> LabelScore:
    true_positives = sum(label in g and label in p for g, p in zip(gold, predicted, strict=True))
    support = sum(label in g for g in gold)
    predicted_count = sum(label in p for p in predicted)
    if support + predicted_count == 0:
        return LabelScore(label, 0, 0, None)
    # F1 = 2·TP / (2·TP + FP + FN), and FP + FN + 2·TP = support + predicted.
    return LabelScore(
        label, support, predicted_count, 2 * true_positives / (support + predicted_count)
    )


def family_scores(
    gold: Sequence[frozenset[str]],
    predicted: Sequence[frozenset[str]],
    labels: Sequence[str],
) -> tuple[FamilyScore, ...]:
    """One score per family, in the order the families first appear in `labels`."""
    if len(gold) != len(predicted):
        raise ValueError(f"{len(gold)} gold and {len(predicted)} predicted label sets")
    families = list(dict.fromkeys(family_of(label) for label in labels))
    scores: list[FamilyScore] = []
    for family in families:
        per_label = tuple(
            label_score(label, gold, predicted) for label in labels if family_of(label) == family
        )
        defined = [s.f1 for s in per_label if s.f1 is not None]
        macro = sum(defined) / len(defined) if defined else None
        scores.append(FamilyScore(family, macro, per_label))
    return tuple(scores)
