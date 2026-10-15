"""The hand-labelled examples the own model is trained on (ADR-0016).

Pure: what a labelled example is, the labels the model learns and how an example becomes the
multi-hot vector SetFit trains on, and the check that the training set shares no article with the
blind test set.
"""

from collections.abc import Collection, Sequence
from dataclasses import dataclass

from datos.governments.application.published import CompetenceLevel


class TrainingSetError(Exception):
    """The training set cannot be used: a bad row, a repeated article or one from the test set."""


@dataclass(frozen=True, slots=True)
class LabelledExample:
    """One article labelled by the author. Communities are left out: the model skips them."""

    article_id: int
    sectors: frozenset[str]
    levels: frozenset[CompetenceLevel]
    stratum: str  # "random" or "enriched": how the article came into the sample
    unsure: bool  # the author hesitated; labels are final after the second pass


def model_labels(sector_ids: Collection[str]) -> tuple[str, ...]:
    """The labels the model learns, in a fixed order: sectors by id, then levels as the enum has.

    The order is the model's: it is saved with the weights and the predictor reads it back, so it
    cannot depend on anything that might change (the order a database returns rows in).
    """
    return tuple(f"sector:{s}" for s in sorted(sector_ids)) + tuple(
        f"level:{level.value}" for level in CompetenceLevel
    )


def multi_hot(example: LabelledExample, labels: Sequence[str]) -> list[int]:
    """1 for each label the author gave the article, 0 for the rest, in the order of `labels`."""
    given = {f"sector:{s}" for s in example.sectors} | {
        f"level:{lv.value}" for lv in example.levels
    }
    unknown = given - set(labels)
    if unknown:
        raise TrainingSetError(
            f"article {example.article_id}: labels the model does not learn: {sorted(unknown)}"
        )
    return [1 if label in given else 0 for label in labels]


def check_usable(examples: Sequence[LabelledExample], test_ids: Collection[int]) -> None:
    """Refuse a training set with a repeated article or one that is also in the blind test set.

    A test-set article used for training would make the evaluation of task 18 meaningless, and the
    sampler already avoids it: this is the last check, in case the file came another way.
    """
    if not examples:
        raise TrainingSetError("the training set is empty")
    ids = [e.article_id for e in examples]
    repeated = sorted({i for i in ids if ids.count(i) > 1})
    if repeated:
        raise TrainingSetError(f"articles labelled more than once: {repeated[:5]}")
    shared = sorted(set(ids) & set(test_ids))
    if shared:
        raise TrainingSetError(f"articles that are also in the blind test set: {shared[:5]}")
