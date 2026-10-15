"""The files of a labelled set (data/train/, data/eval/): its sample and the set itself.

Only ids and labels are written, never a headline or a lead (sources audit: the lead is processed,
never published). The output is sorted by article id and written whole, so the same answers give
the same bytes and the file's hash says which labels a model was trained on.
"""

import json
from pathlib import Path

from pydantic import BaseModel, ValidationError

from datos.classification.domain.labelled_export import LabelledRow
from datos.classification.domain.training_set import TrainingSetError


class _SampleRow(BaseModel):
    article_id: int
    stratum: str


def read_sample_strata(path: Path) -> dict[int, str]:
    """article id → stratum, from the sample file the labelling tasks were made from."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as error:
        raise TrainingSetError(f"{path}: not found") from error
    strata: dict[int, str] = {}
    for number, line in enumerate(lines, start=1):
        try:
            row = _SampleRow.model_validate_json(line)
        except ValidationError as error:
            raise TrainingSetError(f"{path}:{number}: {error}") from error
        strata[row.article_id] = row.stratum
    return strata


def write_labelled_set(path: Path, rows: tuple[LabelledRow, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(
                {
                    "article_id": r.article_id,
                    "stratum": r.stratum,
                    "communities": list(r.communities),
                    "sectors": list(r.sectors),
                    "government_levels": list(r.government_levels),
                    "unsure": r.unsure,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
            for r in rows
        ),
        encoding="utf-8",
    )
