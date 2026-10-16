import json
import xml.etree.ElementTree as ElementTree
from datetime import UTC, datetime
from pathlib import Path

from datos.classification.application.sample_for_labelling import Sample
from datos.classification.domain.sampling import Candidate, Quota, SampledArticle, Stratum
from datos.classification.infrastructure.sample_files import write_sample

UNTIL = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)


def _sample() -> Sample:
    first = Candidate(1, "el-pais", "https://a.example/1", "Primer titular", "Primera entradilla.")
    second = Candidate(2, "okdiario", "https://a.example/2", "Segundo titular", None)
    return Sample(
        articles=(
            SampledArticle(1, "el-pais", "https://a.example/1", Stratum.RANDOM),
            SampledArticle(2, "okdiario", "https://a.example/2", Stratum.ENRICHED),
        ),
        texts={1: first, 2: second},
        quotas={"el-pais": Quota(1, 0), "okdiario": Quota(0, 1)},
        shortfalls=(),
        enriched_available={"el-pais": 3, "okdiario": 5},
    )


def _write(tmp_path: Path) -> tuple[list[dict[str, dict[str, object]]], dict[str, object]]:
    _, meta, tasks = write_sample(
        _sample(),
        name="s1",
        out_dir=tmp_path / "sets",
        tasks_dir=tmp_path / "tasks",
        seed=1,
        until=UNTIL,
        terms_version="terms-v1",
        tags_by_id={1: ("Sanidad", "Madrid")},
        tag_stoplist="list-v1",
    )
    return json.loads(tasks.read_text("utf-8")), json.loads(meta.read_text("utf-8"))


def test_each_task_shows_the_tags_the_model_will_read_as_one_line(tmp_path: Path) -> None:
    tasks, _ = _write(tmp_path)

    assert tasks[0]["data"]["tags"] == "Etiquetas: Sanidad, Madrid."
    assert tasks[0]["data"]["headline"] == "Primer titular"


def test_an_article_without_tags_has_an_empty_line_so_the_screen_shows_nothing(
    tmp_path: Path,
) -> None:
    tasks, _ = _write(tmp_path)

    assert tasks[1]["data"]["tags"] == ""


def test_the_tasks_never_carry_the_outlet(tmp_path: Path) -> None:
    tasks, _ = _write(tmp_path)

    assert set(tasks[0]["data"]) == {"article_id", "headline", "tags", "lead"}


def test_the_sample_says_which_stoplist_the_author_saw(tmp_path: Path) -> None:
    _, meta = _write(tmp_path)

    assert meta["tag_stoplist_version"] == "list-v1"


def test_the_screen_shows_the_tags_between_the_headline_and_the_lead() -> None:
    # Our own versioned file, not untrusted input.
    root = ElementTree.parse("data/labelling/label-studio.xml").getroot()  # noqa: S314

    shown = [(e.tag, e.get("value")) for e in root if e.tag in {"Header", "Text"}][:3]

    assert shown == [("Header", "$headline"), ("Text", "$tags"), ("Text", "$lead")]
