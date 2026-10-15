"""The labelled sets never share an article: a test-set article used for training would make the
evaluation of ADR-0016 meaningless."""

import json
from pathlib import Path

from datos.classification.infrastructure.sample_files import labelled_ids


def _ids(directory: Path) -> set[int]:
    return labelled_ids([directory])


def test_no_article_is_both_in_a_training_set_and_in_the_blind_test_set() -> None:
    assert not _ids(Path("data/train")) & _ids(Path("data/eval"))


def test_no_labelled_set_stores_a_headline_or_a_lead() -> None:
    # Only ids, outlets, URLs, strata and labels are versioned (sources audit, section 7).
    for directory in (Path("data/train"), Path("data/eval")):
        for path in directory.glob("*.jsonl"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    assert not {"headline", "lead"} & set(json.loads(line)), path


def test_labelled_ids_reads_every_jsonl_of_a_directory(tmp_path: Path) -> None:
    (tmp_path / "one.jsonl").write_text('{"article_id": 1}\n{"article_id": 2}\n', encoding="utf-8")
    (tmp_path / "two.jsonl").write_text('{"article_id": 3}\n\n', encoding="utf-8")
    (tmp_path / "notes.json").write_text('{"article_id": 99}', encoding="utf-8")

    assert labelled_ids([tmp_path]) == {1, 2, 3}
