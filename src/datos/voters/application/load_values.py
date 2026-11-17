"""Load a dimension's municipal percentages for a year (higher education, aged 70 or over, born
abroad), from the INE's table files (spec AC4 of voters-dimensions; voters-age-origin)."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from datos.voters.domain.municipal_value import (
    MunicipalValue,
    changed_since,
    unknown_province_problems,
)
from datos.voters.domain.share import ShareCount, share_values


@dataclass(frozen=True, slots=True)
class ValueSourceFile:
    """A table file of the INE as the use case needs it: what identifies it and its counts."""

    source_url: str
    source_file: str
    sha256: str
    counts: Sequence[ShareCount]


@dataclass(frozen=True, slots=True)
class ValueLoad:
    """One file and the values to store as its load: those that came from it and are new."""

    source_url: str
    source_file: str
    sha256: str
    values: Sequence[MunicipalValue]


class ValueRepository(Protocol):
    def province_ids(self) -> set[str]: ...

    def latest_values(self, dimension: str, year: int) -> dict[str, Decimal]:
        """The latest stored value of every municipality for the dimension and year."""
        ...

    def record(self, dimension: str, loads: Sequence[ValueLoad]) -> None:
        """Store these loads and their values in one transaction."""
        ...


class InvalidValuesError(Exception):
    def __init__(self, problems: Sequence[str]) -> None:
        super().__init__(f"{len(problems)} problem(s):\n- " + "\n- ".join(problems))
        self.problems = list(problems)


def load_values(
    dimension: str, files: Sequence[ValueSourceFile], repository: ValueRepository, *, year: int
) -> int:
    """Check the year's percentages of a dimension and store the new or revised ones; returns how
    many. `dimension` is the one of its loads (migration 0017), e.g. "education".

    A municipality is in one file only (in two it is a problem), and its value is stored in that
    file's load. An unchanged value is not stored again, and a file with nothing new is not
    recorded."""
    # A file with no count of the year is a wrong file or a wrong year, never "nothing new": with
    # the other one alone, its municipalities would silently have no value.
    empty = [
        f"{file.source_file}: no {dimension} count of any municipality for {year}"
        for file in files
        if not file.counts
    ]
    if empty:
        raise InvalidValuesError(empty)
    counts = [count for file in files for count in file.counts]
    values, problems = share_values(counts, year)
    problems += unknown_province_problems(values, repository.province_ids())
    if problems:
        raise InvalidValuesError(problems)
    changed = changed_since(values, repository.latest_values(dimension, year))
    loads = _loads(files, changed)
    if loads:
        repository.record(dimension, loads)
    return len(changed)


def _loads(files: Sequence[ValueSourceFile], changed: Sequence[MunicipalValue]) -> list[ValueLoad]:
    """The changed values grouped under the file their municipality's counts came from."""
    owner = {count.municipality_code: file for file in files for count in file.counts}
    loads = [
        ValueLoad(
            file.source_url,
            file.source_file,
            file.sha256,
            [v for v in changed if owner[v.municipality_code] is file],
        )
        for file in files
    ]
    return [load for load in loads if load.values]
