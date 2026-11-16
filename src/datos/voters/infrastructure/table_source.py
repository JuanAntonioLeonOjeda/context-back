"""Reader of the INE's Censo anual de población tables, for any dimension made as a share.

The tables of education (66620, 66623), age (66620) and place of birth (66621) are the same kind
of file (docs/sources-audit.md, sections 12 and 13): one row per municipality, sex, other
categories and period, a count in the last column. What changes is which column says what a
row counts and which of its values are the whole and the part. A `TableLayout` states that, so
a new dimension is a new layout and not a new reader.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field

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
