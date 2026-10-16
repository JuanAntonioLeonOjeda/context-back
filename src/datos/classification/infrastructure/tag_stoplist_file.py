"""Reads `data/classification/tag-stoplist.csv`; a bad row fails with its line number."""

import csv
from pathlib import Path

from pydantic import BaseModel, ValidationError, field_validator

from datos.classification.domain.tag_stoplist import MatchKind, Reason, StoplistEntry, tag_key
from datos.classification.infrastructure.sample_files import file_version

DEFAULT_STOPLIST = Path("data/classification/tag-stoplist.csv")


class InvalidTagStoplistError(Exception):
    """The file is missing, has no entries or has a row that does not validate."""


class _Row(BaseModel):
    tag: str
    match: MatchKind
    reason: Reason

    @field_validator("tag")
    @classmethod
    def _in_key_form(cls, value: str) -> str:
        # A tag written in capitals would never match a key: reject it instead of ignoring it.
        if not value or tag_key(value) != value:
            raise ValueError(f"not in key form (lower case, single spaces, not empty): {value!r}")
        return value


def read_tag_stoplist(path: Path = DEFAULT_STOPLIST) -> list[StoplistEntry]:
    entries: list[StoplistEntry] = []
    try:
        with path.open(encoding="utf-8", newline="") as file:
            for line, raw in enumerate(csv.DictReader(file), start=2):
                try:
                    row = _Row.model_validate(raw)
                except ValidationError as error:
                    raise InvalidTagStoplistError(f"{path}:{line}: {error}") from error
                entries.append(StoplistEntry(row.tag, row.match, row.reason))
    except FileNotFoundError as error:
        raise InvalidTagStoplistError(f"{path}: not found") from error
    if not entries:
        raise InvalidTagStoplistError(f"{path}: no entries")
    return entries


def tag_stoplist_version(path: Path = DEFAULT_STOPLIST) -> str:
    """A hash of the file: a model's card and a sample record which list they used."""
    return file_version(path)
