"""Reader of the INE's Censo anual de población, by level of studies (tables 66620 and 66623).

Checked on 2026-11-16 (docs/sources-audit.md, section 12): the API refuses these tables for their
volume, so the table files (`csv_bdsc`) are read instead. UTF-8 with a BOM (although the header
says ISO-8859-15), `;` between columns, and thousands written with a dot (`2.503`). Each file
has one row per municipality, sex, level of studies and period; 66620 (municipalities of 500
people or more) adds an age column and 66623 (50 to 499) has none.
"""

import re
from collections.abc import Mapping

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
