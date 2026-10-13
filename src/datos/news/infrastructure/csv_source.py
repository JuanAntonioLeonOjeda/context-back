"""Reads the versioned outlets and feeds CSVs under data/news/."""

import csv
from pathlib import Path

from pydantic import BaseModel, ValidationError, field_validator

from datos.news.domain.outlet import Feed, FeedKind, Outlet


class InvalidNewsFileError(Exception):
    pass


class _OutletRow(BaseModel):
    id: str
    name: str
    home_url: str
    scope: str
    region_id: str | None
    external_llm_allowed: bool

    @field_validator("region_id", mode="before")
    @classmethod
    def _empty_as_none(cls, value: object) -> object:
        return None if value == "" else value


class _FeedRow(BaseModel):
    outlet_id: str
    kind: FeedKind
    url: str
    section: str
    needs_page_fetch: bool


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def read_outlets(path: Path) -> list[Outlet]:
    outlets: list[Outlet] = []
    for index, raw in enumerate(_rows(path)):
        try:
            row = _OutletRow.model_validate(raw)
        except ValidationError as error:
            raise InvalidNewsFileError(f"{path.name} line {index + 2}: {error}") from error
        outlets.append(
            Outlet(
                row.id, row.name, row.home_url, row.scope, row.region_id, row.external_llm_allowed
            )
        )
    ids = [o.id for o in outlets]
    if len(ids) != len(set(ids)):
        raise InvalidNewsFileError(f"{path.name}: duplicate outlet id")
    return outlets


def read_feeds(path: Path, outlets: list[Outlet]) -> list[Feed]:
    known = {o.id for o in outlets}
    feeds: list[Feed] = []
    for index, raw in enumerate(_rows(path)):
        try:
            row = _FeedRow.model_validate(raw)
        except ValidationError as error:
            raise InvalidNewsFileError(f"{path.name} line {index + 2}: {error}") from error
        if row.outlet_id not in known:
            raise InvalidNewsFileError(
                f"{path.name} line {index + 2}: unknown outlet {row.outlet_id}"
            )
        feeds.append(Feed(row.outlet_id, row.kind, row.url, row.section, row.needs_page_fetch))
    return feeds
