"""Reader of the INE's Censo anual de población tables, for any dimension made as a share.

The tables of education (66620, 66623), age (66620) and place of birth (66621) are the same kind
of file (docs/sources-audit.md, sections 12 and 13): one row per municipality, sex, other
categories and period, a count in the last column. What changes is which column says what a
row counts and which of its values are the whole and the part. A `TableLayout` states that, so
a new dimension is a new layout and not a new reader.
"""

import csv
import hashlib
import re
from collections import defaultdict
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

from datos.voters.application.load_education import EducationSourceFile
from datos.voters.domain.share import Component, ShareCount

MUNICIPALITY = "municipality"  # the first column, whose title differs between the files
PERIOD, COUNT = "Periodo", "Total"  # in every table; the count column is called "Total" too

_MUNICIPALITY = re.compile(r"^(\d{5}) \S")  # '01006 Armiñón'
_THOUSANDS = re.compile(r"^\d{1,3}(\.\d{3})*$|^\d+$")  # '2.503', '215'


class InvalidTableFileError(Exception):
    """A row of the file is not what the INE's tables look like."""


@dataclass(frozen=True, slots=True)
class TableLayout:
    """What a table's rows mean for one dimension.

    `category` is the column that says what a row counts, `total` its value for the whole and
    `part` its values that make up the part (several for age: 70-79, 80-89 and 90 or more).
    `fixed` pins every other column to the one value the share uses (all sexes, all levels of
    studies...); `optional` names the pinned columns a file may not have, as 66623 has no age.
    """

    category: str
    total: str
    part: frozenset[str]
    fixed: Mapping[str, str]
    optional: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        # A layout where the whole is also a part, or with no part, would give a share that means
        # nothing: it is a mistake of whoever writes the layout, said when it is written.
        if not self.part or self.total in self.part:
            raise ValueError(
                f"layout of {self.category!r}: the part must exist and exclude the total"
            )
        if self.category in self.fixed or not self.optional <= set(self.fixed):
            raise ValueError(f"layout of {self.category!r}: bad fixed or optional columns")


@dataclass(frozen=True, slots=True)
class CategoryCount:
    """The count of one row the share uses: which municipality, which value of the category."""

    municipality_code: str
    category: str
    count: int


def category_count(layout: TableLayout, row: Mapping[str, str], year: int) -> CategoryCount | None:
    """The count a row gives, or None when the row is not one the share uses: another period,
    another value of a pinned column or a value of the category that is neither the whole nor a
    part. A row that is used but cannot be read (municipality or number) raises, never a guess."""
    category = row[layout.category]
    if row[PERIOD] != str(year) or (category != layout.total and category not in layout.part):
        return None
    if any(_pinned_value(layout, row, column) != wanted for column, wanted in layout.fixed.items()):
        return None
    return CategoryCount(_municipality_code(row[MUNICIPALITY]), category, _count(row[COUNT]))


def _pinned_value(layout: TableLayout, row: Mapping[str, str], column: str) -> str:
    # A column the file may lack counts as already having the wanted value, never as a mismatch.
    if column in layout.optional and column not in row:
        return layout.fixed[column]
    return row[column]


def _municipality_code(cell: str) -> str:
    found = _MUNICIPALITY.match(cell)
    if found is None:
        raise InvalidTableFileError(f"municipality {cell!r}: no 5-digit INE code at the start")
    return found.group(1)


def _count(cell: str) -> int:
    if not _THOUSANDS.match(cell):
        raise InvalidTableFileError(f"count {cell!r} is not a whole number")
    return int(cell.replace(".", ""))


def read_table_file(
    path: Path, year: int, layout: TableLayout, *, source_url: str
) -> EducationSourceFile:
    """Reads a table file of the INE in one pass and in constant memory (66620 is 266 MB): the
    hash is computed over the bytes while the rows are read, so the file is not read twice."""
    digest = hashlib.sha256()
    try:
        with path.open("rb") as file:
            rows = csv.reader(_decoded_lines(file, digest), delimiter=";")
            columns = _columns(layout, next(rows, []))
            found = _fold(
                count
                for row in rows
                if row  # a blank line, as at the end of the file
                if (count := category_count(layout, _named(columns, row), year)) is not None
            )
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        # A file that is missing, not UTF-8 (the header says ISO-8859-15, the bytes are UTF-8) or
        # not CSV is a broken input like any other: said and refused, never a traceback.
        raise InvalidTableFileError(f"{path.name}: {error}") from error
    return EducationSourceFile(
        source_url, path.name, digest.hexdigest(), _share_counts(layout, found)
    )


def _decoded_lines(file: BinaryIO, digest: "hashlib._Hash") -> Iterator[str]:
    """The lines of the file as text, each one hashed as its bytes. Only the first carries the
    BOM, which `utf-8-sig` drops."""
    for number, line in enumerate(file):
        digest.update(line)
        yield line.decode("utf-8-sig" if number == 0 else "utf-8")


def _columns(layout: TableLayout, header: list[str]) -> list[str]:
    """The header with its first column named MUNICIPALITY, or an error when the table is not
    the one the layout describes: a changed layout must stop the load, not shift the columns."""
    names = header[1:]
    required = {PERIOD, COUNT, layout.category, *layout.fixed} - layout.optional
    allowed = required | layout.optional
    if not required <= set(names) or not set(names) <= allowed:
        raise InvalidTableFileError(f"unexpected columns: {header!r}")
    return [MUNICIPALITY, *names]


def _named(columns: list[str], row: list[str]) -> dict[str, str]:
    if len(row) != len(columns):
        raise InvalidTableFileError(f"row with {len(row)} cells, expected {len(columns)}")
    return dict(zip(columns, row, strict=True))


def _fold(counts: Iterator[CategoryCount]) -> dict[str, dict[str, int]]:
    """The counts by municipality and value of the category. The same value twice for a
    municipality is an error: summing it would count a duplicated row as if it were data."""
    found: dict[str, dict[str, int]] = defaultdict(dict)
    for count in counts:
        if count.category in found[count.municipality_code]:
            raise InvalidTableFileError(
                f"municipality {count.municipality_code}: {count.category!r} is repeated"
            )
        found[count.municipality_code][count.category] = count.count
    return found


def _share_counts(layout: TableLayout, found: Mapping[str, Mapping[str, int]]) -> list[ShareCount]:
    """The whole and the part of every municipality, the part being the sum of its values. A
    municipality with some of the part's values but not all is refused: its sum would be short."""
    counts: list[ShareCount] = []
    for code in sorted(found):
        values = found[code]
        if layout.total in values:
            counts.append(ShareCount(code, Component.TOTAL, values[layout.total]))
        present = layout.part & values.keys()
        if present and present != layout.part:
            missing = sorted(layout.part - present)
            raise InvalidTableFileError(f"municipality {code}: no count for {missing}")
        if present:
            counts.append(ShareCount(code, Component.PART, sum(values[v] for v in present)))
    return counts
