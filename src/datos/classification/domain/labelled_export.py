"""From the labelling tool's answers to the rows of a labelled set (task 15, labelling guide).

Pure: what each task got, the sample it came from and the vocabulary in, the rows out. The rules are
the guide's: one answer per article, no label outside the vocabulary, an empty answer means "none of
these" (not "not labelled"), and a skipped or unanswered article is reported, never turned into an
empty label.
"""

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass

from datos.classification.domain.training_set import TrainingSetError
from datos.governments.application.published import CompetenceLevel

COMMUNITY_IDS = frozenset(f"ccaa-{n:02d}" for n in range(1, 20))  # appendix of the guide
UNSURE = "unsure"


@dataclass(frozen=True, slots=True)
class Answer:
    """What the author chose for one article, by field (`sectors`, `communities`, ...)."""

    choices: Mapping[str, frozenset[str]]


@dataclass(frozen=True, slots=True)
class ExportedTask:
    article_id: int
    answers: tuple[Answer, ...]  # the answers that were not skipped


@dataclass(frozen=True, slots=True)
class LabelledRow:
    article_id: int
    stratum: str
    communities: tuple[str, ...]
    sectors: tuple[str, ...]
    government_levels: tuple[str, ...]
    unsure: bool


@dataclass(frozen=True, slots=True)
class Assembly:
    rows: tuple[LabelledRow, ...]  # by article id
    unlabelled: tuple[int, ...]  # in the sample and in the tool, with no answer yet
    not_in_tool: tuple[int, ...]  # in the sample, never sent to the tool


def assemble(
    tasks: Sequence[ExportedTask],
    strata: Mapping[int, str],
    *,
    sector_ids: Collection[str],
) -> Assembly:
    """The rows of every answered article; the others are named, not guessed."""
    ids = [t.article_id for t in tasks]
    repeated = sorted({i for i in ids if ids.count(i) > 1})
    if repeated:
        raise TrainingSetError(f"articles in the export more than once: {repeated[:5]}")
    foreign = sorted(set(ids) - set(strata))
    if foreign:
        raise TrainingSetError(f"articles that are not in the sample: {foreign[:5]}")

    rows: list[LabelledRow] = []
    unlabelled: list[int] = []
    for task in sorted(tasks, key=lambda t: t.article_id):
        if not task.answers:
            unlabelled.append(task.article_id)
            continue
        if len(task.answers) > 1:
            raise TrainingSetError(
                f"article {task.article_id}: {len(task.answers)} answers; keep one in the tool"
            )
        rows.append(_row(task.article_id, strata[task.article_id], task.answers[0], sector_ids))
    return Assembly(tuple(rows), tuple(unlabelled), tuple(sorted(set(strata) - set(ids))))


def _row(article_id: int, stratum: str, answer: Answer, sector_ids: Collection[str]) -> LabelledRow:
    fields = {"communities", "sectors", "government_levels", UNSURE}
    unknown_fields = sorted(set(answer.choices) - fields)
    if unknown_fields:
        raise TrainingSetError(f"article {article_id}: unknown fields {unknown_fields}")
    return LabelledRow(
        article_id=article_id,
        stratum=stratum,
        communities=_valid(article_id, answer, "communities", COMMUNITY_IDS),
        sectors=_valid(article_id, answer, "sectors", frozenset(sector_ids)),
        government_levels=_valid(
            article_id,
            answer,
            "government_levels",
            frozenset(level.value for level in CompetenceLevel),
        ),
        unsure=UNSURE in answer.choices.get(UNSURE, frozenset()),
    )


def _valid(
    article_id: int, answer: Answer, field: str, vocabulary: Collection[str]
) -> tuple[str, ...]:
    chosen = answer.choices.get(field, frozenset())
    outside = sorted(chosen - set(vocabulary))
    if outside:
        raise TrainingSetError(f"article {article_id}: {field} outside the vocabulary: {outside}")
    return tuple(sorted(chosen))
