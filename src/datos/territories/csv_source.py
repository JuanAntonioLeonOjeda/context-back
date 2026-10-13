"""Reads the versioned territories CSV.

Reference data fails fast: one invalid row aborts the whole load, unlike news feeds,
where a bad item is logged and dropped.
"""

import csv
from pathlib import Path

from pydantic import BaseModel, ValidationError, field_validator

from datos.territories.territory import Level, Territory


class InvalidTerritoriesFileError(Exception):
    pass


class _Row(BaseModel):
    id: str
    ine_code: str | None
    name: str
    level: Level
    parent_id: str | None

    @field_validator("ine_code", "parent_id", mode="before")
    @classmethod
    def _empty_as_none(cls, value: object) -> object:
        return None if value == "" else value


def read_territories(path: Path) -> list[Territory]:
    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    territories = [_parse(row, line=index + 2) for index, row in enumerate(rows)]
    _check_unique_ids(territories)
    return territories


def _parse(row: dict[str, str], line: int) -> Territory:
    try:
        parsed = _Row.model_validate(row)
    except ValidationError as error:
        raise InvalidTerritoriesFileError(f"line {line}: {error}") from error
    return Territory(
        id=parsed.id,
        ine_code=parsed.ine_code,
        name=parsed.name,
        level=parsed.level,
        parent_id=parsed.parent_id,
    )


def _check_unique_ids(territories: list[Territory]) -> None:
    seen: set[str] = set()
    for territory in territories:
        if territory.id in seen:
            raise InvalidTerritoriesFileError(f"duplicate id {territory.id}")
        seen.add(territory.id)
