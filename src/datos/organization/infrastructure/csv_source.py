"""Reads the curated organisation files under data/organization/.

Reference data fails fast: a row that does not validate stops the load with its file and line,
and so does a header that is not the expected one. Rules that need several rows (a parent that
exists, periods that do not overlap) are the domain's (`dataset_problems`).
"""

import csv
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
)

from datos.organization.domain.body import Body, BodyKind, BodyLevel, Holder
from datos.organization.domain.boxes import Competence

BODIES_FILE = "bodies.csv"
HOLDERS_FILE = "holders.csv"
COMPETENCES_FILE = "competences.csv"

# A text that is not empty once the spaces around it are gone.
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
# Every row says where it comes from, and it must be an address a reader can open.
SourceUrl = Annotated[str, Field(pattern=r"^https?://\S+$")]


class InvalidOrganizationFileError(Exception):
    """The file is missing, has other columns than expected or has a row that does not validate."""


class _Row(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def _blank_as_none(cls, value: object) -> object:
        # An optional cell is left empty; a required one then fails as "none is not a text".
        return None if isinstance(value, str) and not value.strip() else value


class _BodyRow(_Row):
    id: Text
    kind: BodyKind
    level: BodyLevel
    territory_id: Text | None
    name: Text
    parent_id: Text | None
    dir3_id: Text | None
    source_url: SourceUrl


class _HolderRow(_Row):
    body_id: Text
    post_title: Text
    holder_name: Text
    valid_from: date
    valid_to: date | None
    source_url: SourceUrl


class _CompetenceRow(_Row):
    body_id: Text
    summary: Text
    legal_basis: Text
    sector_ids: tuple[Text, ...]
    source_url: SourceUrl

    @field_validator("sector_ids", mode="before")
    @classmethod
    def _split(cls, value: object) -> object:
        # "health|housing"; an empty cell is no sector, a stray bar is an empty one and fails.
        if value is None or (isinstance(value, str) and not value.strip()):
            return ()
        return tuple(value.split("|")) if isinstance(value, str) else value


def read_bodies(path: Path) -> list[Body]:
    return [
        Body(
            id=r.id,
            kind=r.kind,
            level=r.level,
            territory_id=r.territory_id,
            name=r.name,
            parent_id=r.parent_id,
            dir3_id=r.dir3_id,
            source_url=r.source_url,
        )
        for r in _read(path, _BodyRow)
    ]


def read_holders(path: Path) -> list[Holder]:
    return [
        Holder(
            body_id=r.body_id,
            post_title=r.post_title,
            holder_name=r.holder_name,
            valid_from=r.valid_from,
            valid_to=r.valid_to,
            source_url=r.source_url,
        )
        for r in _read(path, _HolderRow)
    ]


def read_competences(path: Path) -> list[Competence]:
    return [
        Competence(
            body_id=r.body_id,
            summary=r.summary,
            legal_basis=r.legal_basis,
            sector_ids=r.sector_ids,
            source_url=r.source_url,
        )
        for r in _read(path, _CompetenceRow)
    ]


def _read[M: _Row](path: Path, model: type[M]) -> list[M]:
    expected = list(model.model_fields)
    rows: list[M] = []
    try:
        # utf-8-sig: a file saved from a spreadsheet may start with a byte order mark.
        with path.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            _check_header(path, reader.fieldnames, expected)
            for raw in reader:
                try:
                    rows.append(model.model_validate(raw))
                except ValidationError as error:
                    raise InvalidOrganizationFileError(
                        f"{path}:{reader.line_num}: {_describe(error)}"
                    ) from error
    except FileNotFoundError as error:
        raise InvalidOrganizationFileError(f"{path}: not found") from error
    return rows


def _check_header(path: Path, found: Sequence[str] | None, expected: list[str]) -> None:
    if list(found or []) != expected:
        raise InvalidOrganizationFileError(
            f"{path}:1: the columns are {list(found or [])}, expected {expected}"
        )


def _describe(error: ValidationError) -> str:
    """Each field that failed and why, in the file's own column names."""
    return "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in error.errors())


def read_organization(data_dir: Path) -> tuple[list[Body], list[Holder], list[Competence]]:
    """The three files of `data/organization/` (or another folder with the same three names)."""
    return (
        read_bodies(data_dir / BODIES_FILE),
        read_holders(data_dir / HOLDERS_FILE),
        read_competences(data_dir / COMPETENCES_FILE),
    )
