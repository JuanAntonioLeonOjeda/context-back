"""Reads the hand-labelled training set from its JSON Lines file (data/train/, ADR-0016).

One article per line, as the export of task 15 writes it:
`{"article_id": 7, "stratum": "random", "sectors": ["health"], "government_levels": ["state"],
"unsure": false, ...}`. Communities and the other keys of the line (outlet, URL) are ignored: the
model learns sectors and levels only. The file holds ids and labels, never a headline or a lead.
"""

import json
from collections.abc import Collection
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ValidationError, field_validator

from datos.classification.domain.training_set import LabelledExample, TrainingSetError
from datos.governments.application.published import CompetenceLevel


class _Row(BaseModel):
    article_id: int
    stratum: Literal["random", "enriched"]
    sectors: list[str]
    government_levels: list[str]
    unsure: bool = False

    @field_validator("sectors", "government_levels")
    @classmethod
    def _no_repeats(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("a label is listed twice")
        return value


def read_training_set(path: Path, *, sector_ids: Collection[str]) -> list[LabelledExample]:
    known_sectors = frozenset(sector_ids)
    examples: list[LabelledExample] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as error:
        raise TrainingSetError(f"{path}: not found") from error
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        examples.append(_example(path, number, line, known_sectors))
    return examples


def _example(path: Path, number: int, line: str, known_sectors: frozenset[str]) -> LabelledExample:
    try:
        row = _Row.model_validate(json.loads(line))
    except (json.JSONDecodeError, ValidationError) as error:
        raise TrainingSetError(f"{path}:{number}: {error}") from error
    unknown_sectors = set(row.sectors) - known_sectors
    if unknown_sectors:
        raise TrainingSetError(f"{path}:{number}: unknown sectors {sorted(unknown_sectors)}")
    try:
        levels = frozenset(CompetenceLevel(value) for value in row.government_levels)
    except ValueError as error:
        raise TrainingSetError(f"{path}:{number}: {error}") from error
    return LabelledExample(
        article_id=row.article_id,
        sectors=frozenset(row.sectors),
        levels=levels,
        stratum=row.stratum,
        unsure=row.unsure,
    )
