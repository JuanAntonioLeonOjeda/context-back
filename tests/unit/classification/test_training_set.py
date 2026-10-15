"""The training set of the own model: its labels, its file and its disjointness from the test."""

import json
from pathlib import Path

import pytest

from datos.classification.domain.text import article_text
from datos.classification.domain.training_set import (
    LabelledExample,
    TrainingSetError,
    check_usable,
    model_labels,
    multi_hot,
)
from datos.classification.infrastructure.setfit_classifier import SetFitClassifier
from datos.classification.infrastructure.training_set_file import read_training_set
from datos.governments.application.published import CompetenceLevel

SECTORS = ["housing", "education", "health"]  # deliberately not in order
STATE, CCAA, LOCAL = CompetenceLevel.STATE, CompetenceLevel.CCAA, CompetenceLevel.LOCAL


def example(
    article_id: int = 1,
    sectors: frozenset[str] = frozenset(),
    levels: frozenset[CompetenceLevel] = frozenset(),
) -> LabelledExample:
    return LabelledExample(article_id, sectors, levels, stratum="random", unsure=False)


def row(**fields: object) -> str:
    base: dict[str, object] = {
        "article_id": 1,
        "stratum": "random",
        "sectors": ["health"],
        "government_levels": ["state"],
    }
    return json.dumps({**base, **fields})


class TestLabels:
    def test_the_labels_are_sectors_by_id_then_levels_whatever_order_they_come_in(self) -> None:
        assert model_labels(SECTORS) == (
            "sector:education",
            "sector:health",
            "sector:housing",
            "level:state",
            "level:ccaa",
            "level:local",
        )
        assert model_labels(reversed(SECTORS)) == model_labels(SECTORS)  # type: ignore[arg-type]

    def test_an_example_becomes_one_in_each_label_given_and_zero_in_the_rest(self) -> None:
        labels = model_labels(SECTORS)
        health_and_state = example(sectors=frozenset({"health"}), levels=frozenset({STATE}))

        assert multi_hot(health_and_state, labels) == [0, 1, 0, 1, 0, 0]

    def test_an_article_with_no_label_is_a_negative_example_not_an_error(self) -> None:
        assert multi_hot(example(), model_labels(SECTORS)) == [0] * 6

    def test_a_label_the_model_does_not_learn_is_refused(self) -> None:
        with pytest.raises(TrainingSetError, match="sector:transport"):
            multi_hot(example(sectors=frozenset({"transport"})), model_labels(SECTORS))


class TestFile:
    def read(self, tmp_path: Path, *lines: str) -> list[LabelledExample]:
        path = tmp_path / "train-set-v1.jsonl"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return read_training_set(path, sector_ids=SECTORS)

    def test_reads_the_ids_and_the_labels_and_ignores_the_rest_of_the_line(
        self, tmp_path: Path
    ) -> None:
        [read] = self.read(
            tmp_path,
            row(article_id=7, communities=["ccaa-05"], outlet_id="abc", url="https://a.example/7"),
        )

        assert read == LabelledExample(
            7, frozenset({"health"}), frozenset({STATE}), "random", False
        )

    def test_an_article_with_no_sector_and_no_level_is_a_valid_negative(
        self, tmp_path: Path
    ) -> None:
        [read] = self.read(tmp_path, row(sectors=[], government_levels=[], unsure=True))

        assert (read.sectors, read.levels, read.unsure) == (frozenset(), frozenset(), True)

    def test_skips_blank_lines(self, tmp_path: Path) -> None:
        assert len(self.read(tmp_path, row(article_id=1), "", row(article_id=2))) == 2

    @pytest.mark.parametrize(
        ("line", "message"),
        [
            (row(sectors=["transport"]), "unknown sectors"),
            (row(government_levels=["county"]), "county"),
            (row(stratum="other"), "stratum"),
            (row(sectors=["health", "health"]), "listed twice"),
            ('{"article_id": "seven"', "Expecting"),
            ('{"stratum": "random"}', "article_id"),
        ],
    )
    def test_a_bad_row_is_refused_with_its_file_and_line(
        self, tmp_path: Path, line: str, message: str
    ) -> None:
        with pytest.raises(TrainingSetError, match=rf"(?s)train-set-v1\.jsonl:2: .*{message}"):
            self.read(tmp_path, row(), line)

    def test_a_missing_file_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(TrainingSetError, match="not found"):
            read_training_set(tmp_path / "nope.jsonl", sector_ids=SECTORS)


class TestUsable:
    def test_an_empty_set_is_refused(self) -> None:
        with pytest.raises(TrainingSetError, match="empty"):
            check_usable([], test_ids=set())

    def test_an_article_labelled_twice_is_refused(self) -> None:
        with pytest.raises(TrainingSetError, match=r"more than once: \[2\]"):
            check_usable([example(1), example(2), example(2)], test_ids=set())

    def test_an_article_that_is_also_in_the_test_set_is_refused_and_named(self) -> None:
        with pytest.raises(TrainingSetError, match=r"blind test set: \[3\]"):
            check_usable([example(1), example(3)], test_ids={3, 99})

    def test_a_set_with_no_overlap_passes(self) -> None:
        check_usable([example(1), example(2)], test_ids={3, 99})


class TestSameTextInTrainingAndClassifying:
    def test_the_text_is_the_headline_then_the_lead_with_one_space(self) -> None:
        assert article_text("Titular", "Entradilla.") == "Titular Entradilla."
        assert article_text("Solo titular", None) == "Solo titular"
        assert article_text("Solo titular", "") == "Solo titular"
        assert article_text("", None) == ""

    def test_the_classifier_asks_the_model_about_exactly_that_text(self) -> None:
        asked: list[str] = []

        class Recording:
            def probabilities(self, text: str) -> dict[str, float]:
                asked.append(text)
                return {"sector:health": 0.1}

        model = SetFitClassifier(Recording(), model_version="w1", sector_ids={"health"})
        model.classify("Titular", "Entradilla.")
        model.classify("Solo titular", None)

        assert asked == [article_text("Titular", "Entradilla."), article_text("Solo titular", None)]
