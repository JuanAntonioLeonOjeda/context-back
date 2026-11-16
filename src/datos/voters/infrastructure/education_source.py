"""Reader of the INE's Censo anual de población, by level of studies (tables 66620 and 66623).

Checked on 2026-11-16 (docs/sources-audit.md, section 12): the API refuses these tables for their
volume, so the table files (`csv_bdsc`) are read instead. UTF-8 with a BOM (although the header
says ISO-8859-15), `;` between columns, and thousands written with a dot (`2.503`). Each file
has one row per municipality, sex, level of studies and period; 66620 (municipalities of 500
people or more) adds an age column and 66623 (50 to 499) has none.
"""

import csv
import hashlib
import re
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import BinaryIO

from datos.voters.application.load_education import EducationSourceFile
from datos.voters.domain.education import EducationCount, EducationLevel

MUNICIPALITY = "municipality"  # the first column, whose title differs between the files
SEX, AGE, LEVEL, PERIOD, COUNT = "Sexo", "Edad", "Nivel de estudios", "Periodo", "Total"

_ALL_SEXES = "Total"
_AGE_15_OR_MORE = "15 y más años"
_LEVELS = {"Total": EducationLevel.TOTAL, "Educación superior": EducationLevel.HIGHER}
_MUNICIPALITY = re.compile(r"^(\d{5}) \S")  # '01006 Armiñón'
_THOUSANDS = re.compile(r"^\d{1,3}(\.\d{3})*$|^\d+$")  # '2.503', '215'


class InvalidEducationFileError(Exception):
    """A row of the file is not what the INE's tables look like."""


def education_count(row: Mapping[str, str], year: int) -> EducationCount | None:
    """The count a row gives, or None when the row is not one the percentage uses: another sex,
    another age group (in the file that has them), another year or another level of studies.
    A row that is used but cannot be read (municipality or number) raises, never a guess."""
    level = _LEVELS.get(row[LEVEL])
    if (
        level is None
        or row[SEX] != _ALL_SEXES
        or row.get(AGE, _AGE_15_OR_MORE) != _AGE_15_OR_MORE
        or row[PERIOD] != str(year)
    ):
        return None
    return EducationCount(_municipality_code(row[MUNICIPALITY]), level, _count(row[COUNT]))


def _municipality_code(cell: str) -> str:
    found = _MUNICIPALITY.match(cell)
    if found is None:
        raise InvalidEducationFileError(f"municipality {cell!r}: no 5-digit INE code at the start")
    return found.group(1)


def _count(cell: str) -> int:
    if not _THOUSANDS.match(cell):
        raise InvalidEducationFileError(f"count {cell!r} is not a whole number")
    return int(cell.replace(".", ""))


def read_education_file(path: Path, year: int, *, source_url: str) -> EducationSourceFile:
    """Reads a table file of the INE in one pass and in constant memory (66620 is 266 MB): the
    hash is computed over the bytes while the rows are read, so the file is not read twice."""
    digest = hashlib.sha256()
    try:
        with path.open("rb") as file:
            rows = csv.reader(_decoded_lines(file, digest), delimiter=";")
            columns = _columns(next(rows, []))
            counts = tuple(
                count
                for row in rows
                if row  # a blank line, as at the end of the file
                if (count := education_count(_named(columns, row), year)) is not None
            )
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        # A file that is missing, not UTF-8 (the header says ISO-8859-15, the bytes are UTF-8) or
        # not CSV is a broken input like any other: said and refused, never a traceback.
        raise InvalidEducationFileError(f"{path.name}: {error}") from error
    return EducationSourceFile(source_url, path.name, digest.hexdigest(), counts)


def _decoded_lines(file: BinaryIO, digest: "hashlib._Hash") -> Iterator[str]:
    """The lines of the file as text, each one hashed as its bytes. Only the first carries the
    BOM, which `utf-8-sig` drops."""
    for number, line in enumerate(file):
        digest.update(line)
        yield line.decode("utf-8-sig" if number == 0 else "utf-8")


def _columns(header: list[str]) -> list[str]:
    """The header with its first column named MUNICIPALITY, or an error when the table is not
    the one expected: a changed layout must stop the load, not shift the columns."""
    names = header[1:]
    if not {SEX, LEVEL, PERIOD, COUNT} <= set(names) or not set(names) <= {
        SEX,
        AGE,
        LEVEL,
        PERIOD,
        COUNT,
    }:
        raise InvalidEducationFileError(f"unexpected columns: {header!r}")
    return [MUNICIPALITY, *names]


def _named(columns: list[str], row: list[str]) -> dict[str, str]:
    if len(row) != len(columns):
        raise InvalidEducationFileError(f"row with {len(row)} cells, expected {len(columns)}")
    return dict(zip(columns, row, strict=True))


_TABLE_PAGES = {
    "66620.csv": "https://www.ine.es/jaxiT3/Tabla.htm?t=66620",  # 500 people or more
    "66623.csv": "https://www.ine.es/jaxiT3/Tabla.htm?t=66623",  # 50 to 499
}


def table_page(path: Path) -> str:
    """The INE page of the table a file is, by the name the INE gives it when it is downloaded.
    Another name is refused: a file we cannot trace to its table is not loaded."""
    try:
        return _TABLE_PAGES[path.name]
    except KeyError:
        raise InvalidEducationFileError(
            f"{path.name!r} is not one of the education tables: {sorted(_TABLE_PAGES)}"
        ) from None
