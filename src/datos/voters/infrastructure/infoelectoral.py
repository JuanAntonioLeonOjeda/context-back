"""Reader of the Infoelectoral zip of an election by municipality (Ministerio del Interior).

The zip is downloaded by hand (the site answers a bot challenge to automated clients,
docs/sources-audit.md section 10). Layout from its `FICHEROS.doc` (2010), checked on the July 2023
Congreso file: fixed-width records in cp1252, one per line. Positions below are the document's,
from 1; Python slices start at 0, so `[a - 1 : b]`.

Only the municipal totals are read: district rows (municipal district other than `99`) repeat
the total of a big city split by district and would count it twice.
"""

import hashlib
import zipfile
from collections.abc import Iterator
from datetime import date
from pathlib import Path

from datos.voters.domain.election import (
    Candidature,
    CandidatureVotes,
    Election,
    ElectionFile,
    ElectionKind,
    MunicipalResult,
)

# Field 1-2 of every record, and the `xx` of each file's name `nnxxaamm.DAT`.
_KINDS = {"02": ElectionKind.CONGRESO}
# Exact record length of each file (FICHEROS.doc, checked on the 2023 file).
_LENGTHS = {"02": 40, "03": 232, "05": 233, "06": 33}
_MUNICIPAL_TOTAL = "99"


class InvalidElectionFileError(Exception):
    """The zip is not an Infoelectoral file this reader understands; the message says where."""


def read_election_zip(path: Path) -> ElectionFile:
    """Read the identification, candidatures, municipal totals and votes of one zip."""
    data = path.read_bytes()
    with zipfile.ZipFile(path) as archive:
        kind_code, year_month = _name_parts(path.name)
        records = _Records(archive, kind_code, year_month)
        return ElectionFile(
            source_file=path.name,
            sha256=hashlib.sha256(data).hexdigest(),
            election=parse_identification(_only(records.lines("02"))),
            candidatures=tuple(parse_candidature(r) for r in records.lines("03")),
            results=tuple(m for r in records.lines("05") if (m := parse_municipal_result(r))),
            votes=tuple(v for r in records.lines("06") if (v := parse_candidature_votes(r))),
        )


Record = tuple[str, str]  # the line and where it is ("05022307.DAT line 3"), for errors


def parse_identification(record: Record) -> Election:
    """File 02: the kind (1-2), the round (9) and the day it was held (13-20, DDMMYYYY)."""
    line, _ = record
    _expect(line[8] == "1", record, "only one-round elections are supported")
    held_on = _date(line[12:20], record)
    return Election(_kind(line[0:2], record), held_on)


def parse_candidature(record: Record) -> Candidature:
    """File 03: code (9-14), acronym (15-64), name (65-214), national head (227-232)."""
    line, _ = record
    return Candidature(
        code=_digits(line[8:14], record, "candidature code"),
        acronym=line[14:64].strip(),
        name=line[64:214].strip(),
        national_head_code=_digits(line[226:232], record, "national head code"),
    )


def parse_municipal_result(record: Record) -> MunicipalResult | None:
    """File 05: the municipal total (district 99), or None for a district row."""
    line, _ = record
    if line[16:18] != _MUNICIPAL_TOTAL:
        return None
    _expect(line[232] == "S", record, "the data is not marked as official")
    return MunicipalResult(
        municipality_code=_digits(line[11:16], record, "municipality code"),
        municipality_name=line[18:118].strip(),
        census=_number(line[141:149], record, "INE census"),
        blank_votes=_number(line[189:197], record, "blank votes"),
        null_votes=_number(line[197:205], record, "null votes"),
        candidature_votes=_number(line[205:213], record, "votes to candidatures"),
    )


def parse_candidature_votes(record: Record) -> CandidatureVotes | None:
    """File 06: a candidature's votes in a municipal total (district 99), or None."""
    line, _ = record
    if line[14:16] != _MUNICIPAL_TOTAL:
        return None
    return CandidatureVotes(
        municipality_code=_digits(line[9:14], record, "municipality code"),
        candidature_code=_digits(line[16:22], record, "candidature code"),
        votes=_number(line[22:30], record, "votes"),
    )


class _Records:
    """The lines of each `.DAT` of the zip, checked for length, kind and month."""

    def __init__(self, archive: zipfile.ZipFile, kind_code: str, year_month: str) -> None:
        self._archive = archive
        self._kind_code = kind_code
        self._year_month = year_month

    def lines(self, file_type: str) -> Iterator[Record]:
        name = f"{file_type}{self._kind_code}{self._year_month}.DAT"
        try:
            raw = self._archive.read(name)
        except KeyError as error:
            raise InvalidElectionFileError(f"{name} is not in the zip") from error
        for number, line in enumerate(raw.decode("cp1252").splitlines(), start=1):
            where = f"{name} line {number}"
            record = (line, where)
            if len(line) != _LENGTHS[file_type]:
                raise InvalidElectionFileError(
                    f"{where}: {len(line)} characters, expected {_LENGTHS[file_type]}"
                )
            if line[0:2] != self._kind_code or line[2:8] != _expand(self._year_month):
                raise InvalidElectionFileError(f"{where}: another election than the file name's")
            yield record


def _name_parts(file_name: str) -> tuple[str, str]:
    """`02202307_MUNI.zip` → kind `02`, year and month `2307` (the `.DAT` names use `aamm`)."""
    stem = file_name.split("_", 1)[0]
    if len(stem) != 8 or not stem.isdigit() or stem[:2] not in _KINDS:
        raise InvalidElectionFileError(f"{file_name}: not a supported Infoelectoral file name")
    return stem[:2], stem[4:8]


def _expand(year_month: str) -> str:
    """`2307` → `202307`, as fields 3-8 of every record write it."""
    return f"20{year_month}"


def _only(records: Iterator[Record]) -> Record:
    """The single record of file 02."""
    found = list(records)
    if len(found) != 1:
        raise InvalidElectionFileError(f"file 02: {len(found)} records, expected 1")
    return found[0]


def _kind(code: str, record: Record) -> ElectionKind:
    kind = _KINDS.get(code)
    if kind is None:
        raise InvalidElectionFileError(f"{record[1]}: election type {code} is not supported")
    return kind


def _date(ddmmyyyy: str, record: Record) -> date:
    digits = _digits(ddmmyyyy, record, "date")
    try:
        return date(int(digits[4:8]), int(digits[2:4]), int(digits[0:2]))
    except ValueError as error:
        raise InvalidElectionFileError(f"{record[1]}: invalid date {ddmmyyyy}") from error


def _number(field: str, record: Record, what: str) -> int:
    return int(_digits(field, record, what))


def _digits(field: str, record: Record, what: str) -> str:
    _expect(field.isdigit(), record, f"{what} is not a number: {field!r}")
    return field


def _expect(condition: bool, record: Record, message: str) -> None:
    if not condition:
        raise InvalidElectionFileError(f"{record[1]}: {message}")
