"""The evaluation report: one new file per run, never replaced, numbers and versions only."""

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from datos.classification.domain.promotion import EvaluatedArticle, verdicts
from datos.classification.infrastructure.evaluation_report import RunInfo, write_report

LABELS = ("sector:health", "level:ccaa")
GOLD = frozenset({"sector:health", "level:ccaa"})
INFO = RunInfo(
    test_set={"name": "test-set-v1", "file_hash": "abc123", "size": 4},
    rules_version="d74a59205b94",
    tag_stoplist="list-v1",
    model={"name": "train-set-v1-mpnet-seed42", "version": "f00d"},
    seed=20261105,
    run_at=datetime(2026, 11, 5, 10, 30, tzinfo=UTC),
)
ARTICLES = [
    EvaluatedArticle(i, "outlet-a", "random", GOLD, frozenset({"level:ccaa"}), GOLD)
    for i in range(4)
]


def test_writes_the_run_its_versions_and_both_families(tmp_path: Path) -> None:
    path = write_report(tmp_path, INFO, verdicts(ARTICLES, LABELS, seed=1))

    content = json.loads(path.read_text(encoding="utf-8"))
    assert path.name == "20261105T103000+0000-f00d.json"
    assert content["test_set"] == {"name": "test-set-v1", "file_hash": "abc123", "size": 4}
    assert (content["rules_version"], content["model"]["version"]) == ("d74a59205b94", "f00d")
    sector, level = content["families"]
    assert (sector["family"], sector["promoted"]) == ("sector", True)
    assert sector["criterion_1_overall"]["gain"] == pytest.approx(1.0)
    assert sector["criterion_2_outlets"]["outlets"][0]["difference"] == 4
    assert level["criterion_1_overall"]["gain"] == 0.0


def test_a_report_is_never_replaced(tmp_path: Path) -> None:
    write_report(tmp_path, INFO, verdicts(ARTICLES, LABELS, seed=1))

    with pytest.raises(FileExistsError):
        write_report(tmp_path, INFO, verdicts(ARTICLES, LABELS, seed=1))


def test_two_runs_leave_two_files(tmp_path: Path) -> None:
    later = replace(INFO, run_at=datetime(2026, 11, 6, 9, 0, tzinfo=UTC))

    write_report(tmp_path, INFO, verdicts(ARTICLES, LABELS, seed=1))
    write_report(tmp_path, later, verdicts(ARTICLES, LABELS, seed=1))

    assert len(list(tmp_path.glob("*.json"))) == 2
