"""From Label Studio's answers to the rows of a labelled set (task 15)."""

import json
from pathlib import Path

import pytest

from datos.classification.domain.labelled_export import Answer, Assembly, ExportedTask, assemble
from datos.classification.domain.training_set import TrainingSetError
from datos.classification.infrastructure.label_studio_export import read_label_studio_export
from datos.classification.infrastructure.labelled_set_file import (
    read_sample_strata,
    write_labelled_set,
)
from datos.classification.infrastructure.training_set_file import read_training_set

FIXTURE = Path("tests/fixtures/labelstudio/export.json")
SECTORS = frozenset({"education", "health", "housing"})
STRATA = {11: "random", 12: "enriched", 13: "random", 14: "enriched", 15: "random", 16: "random"}


def answer(**fields: set[str]) -> Answer:
    return Answer({name: frozenset(values) for name, values in fields.items()})


def task(article_id: int, *answers: Answer) -> ExportedTask:
    return ExportedTask(article_id, answers)


def assembled(*tasks: ExportedTask, strata: dict[int, str] | None = None) -> Assembly:
    return assemble(list(tasks), strata or STRATA, sector_ids=SECTORS)


def test_reads_the_fixture_without_keeping_any_text() -> None:
    tasks = read_label_studio_export(FIXTURE)

    assert [(t.article_id, len(t.answers)) for t in tasks] == [
        (11, 1),
        (12, 1),
        (13, 1),
        (14, 0),
        (15, 0),
    ]
    assert "Titular" not in repr(tasks)  # headline and lead are not read


def test_the_fixture_gives_rows_with_the_three_families_and_what_is_left() -> None:
    result = assemble(read_label_studio_export(FIXTURE), STRATA, sector_ids=SECTORS)

    first, second, third = result.rows
    assert (first.communities, first.sectors, first.government_levels, first.unsure) == (
        ("ccaa-05",),
        ("housing",),
        ("ccaa", "local"),
        False,
    )
    assert (second.sectors, second.government_levels, second.unsure) == (
        ("health",),
        ("state",),
        True,
    )
    assert (third.sectors, third.government_levels, third.unsure) == ((), (), False)
    assert result.unlabelled == (14, 15)  # skipped and never answered
    assert result.not_in_tool == (16,)


def test_an_answer_with_nothing_chosen_is_a_row_with_no_labels() -> None:
    [row] = assembled(task(13, answer())).rows

    assert (row.sectors, row.government_levels, row.communities) == ((), (), ())


def test_the_stratum_comes_from_the_sample() -> None:
    rows = assembled(task(11, answer()), task(12, answer())).rows

    assert [(r.article_id, r.stratum) for r in rows] == [(11, "random"), (12, "enriched")]


def test_rows_are_by_article_id_whatever_the_order_of_the_export() -> None:
    rows = assembled(task(13, answer()), task(11, answer())).rows

    assert [r.article_id for r in rows] == [11, 13]


@pytest.mark.parametrize(
    ("tasks", "message"),
    [
        ([task(11, answer()), task(11, answer())], "more than once: \\[11\\]"),
        ([task(99, answer())], "not in the sample: \\[99\\]"),
        ([task(11, answer(), answer())], "article 11: 2 answers"),
        (
            [task(11, answer(sectors={"culture"}))],
            "sectors outside the vocabulary: \\['culture'\\]",
        ),
        (
            [task(11, answer(government_levels={"province"}))],
            "government_levels outside the vocabulary",
        ),
        ([task(11, answer(communities={"ccaa-20"}))], "communities outside the vocabulary"),
        ([task(11, answer(topics={"x"}))], "unknown fields \\['topics'\\]"),
    ],
)
def test_refuses_what_cannot_be_a_label(tasks: list[ExportedTask], message: str) -> None:
    with pytest.raises(TrainingSetError, match=message):
        assemble(tasks, STRATA, sector_ids=SECTORS)


def test_a_planned_sector_is_outside_the_vocabulary() -> None:
    with pytest.raises(TrainingSetError, match="outside the vocabulary: \\['work'\\]"):
        assembled(task(11, answer(sectors={"work"})))


def test_the_written_file_is_what_the_training_reader_expects(tmp_path: Path) -> None:
    result = assemble(read_label_studio_export(FIXTURE), STRATA, sector_ids=SECTORS)
    path = tmp_path / "train-set-v1.jsonl"

    write_labelled_set(path, result.rows)
    examples = read_training_set(path, sector_ids=SECTORS)

    assert [(e.article_id, e.stratum, e.unsure) for e in examples] == [
        (11, "random", False),
        (12, "enriched", True),
        (13, "random", False),
    ]
    assert examples[0].sectors == {"housing"}


def test_the_written_file_has_ids_and_labels_never_text(tmp_path: Path) -> None:
    result = assemble(read_label_studio_export(FIXTURE), STRATA, sector_ids=SECTORS)
    path = tmp_path / "train-set-v1.jsonl"

    write_labelled_set(path, result.rows)

    keys = {key for line in path.read_text().splitlines() for key in json.loads(line)}
    assert keys == {
        "article_id",
        "stratum",
        "communities",
        "sectors",
        "government_levels",
        "unsure",
    }
    assert "Titular" not in path.read_text()


def test_the_same_answers_give_the_same_bytes(tmp_path: Path) -> None:
    result = assemble(read_label_studio_export(FIXTURE), STRATA, sector_ids=SECTORS)

    write_labelled_set(tmp_path / "a.jsonl", result.rows)
    write_labelled_set(tmp_path / "b.jsonl", result.rows)

    assert (tmp_path / "a.jsonl").read_bytes() == (tmp_path / "b.jsonl").read_bytes()


def test_the_sample_file_gives_the_strata(tmp_path: Path) -> None:
    sample = tmp_path / "train-sample-v1.jsonl"
    sample.write_text(
        '{"article_id": 1, "outlet_id": "a", "url": "https://x.example", "stratum": "random"}\n'
        '{"article_id": 2, "outlet_id": "b", "url": "https://y.example", "stratum": "enriched"}\n',
        encoding="utf-8",
    )

    assert read_sample_strata(sample) == {1: "random", 2: "enriched"}


def test_an_export_that_is_not_a_list_of_tasks_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "export.json"
    path.write_text('{"tasks": []}', encoding="utf-8")

    with pytest.raises(TrainingSetError, match="expected the list of tasks"):
        read_label_studio_export(path)


def test_a_task_without_an_article_id_is_refused_with_its_number(tmp_path: Path) -> None:
    path = tmp_path / "export.json"
    path.write_text('[{"data": {"headline": "x"}, "annotations": []}]', encoding="utf-8")

    with pytest.raises(TrainingSetError, match="task 1"):
        read_label_studio_export(path)
