"""Reads the versioned governments CSVs under data/governments/.

Reference data fails fast: one invalid row aborts the whole load.
"""

import csv
from datetime import date
from pathlib import Path

from pydantic import BaseModel, ValidationError, field_validator

from datos.governments.domain.government_term import GovernmentTerm, PartyRole, TermParty
from datos.governments.domain.party import Party


class InvalidGovernmentsFileError(Exception):
    pass


class _PartyRow(BaseModel):
    id: str
    name: str
    short_name: str
    colour_hex: str


class _TermRow(BaseModel):
    territory_id: str
    valid_from: date
    valid_to: date | None
    president_name: str
    is_caretaker: bool
    source_url: str

    @field_validator("valid_to", mode="before")
    @classmethod
    def _empty_as_none(cls, value: object) -> object:
        return None if value == "" else value


class _TermPartyRow(BaseModel):
    territory_id: str
    valid_from: date
    party_id: str
    role: PartyRole
    source_url: str


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _parse[T: BaseModel](model: type[T], row: dict[str, str], *, path: Path, line: int) -> T:
    try:
        return model.model_validate(row)
    except ValidationError as error:
        raise InvalidGovernmentsFileError(f"{path.name} line {line}: {error}") from error


def read_parties(path: Path) -> list[Party]:
    parsed = [_parse(_PartyRow, r, path=path, line=i + 2) for i, r in enumerate(_rows(path))]
    parties = [Party(p.id, p.name, p.short_name, p.colour_hex) for p in parsed]
    _check_unique([p.id for p in parties], what="party id", path=path)
    return parties


def read_terms(terms_path: Path, term_parties_path: Path) -> list[GovernmentTerm]:
    """Terms with their parties; a party row without a matching term is an error."""
    party_rows = [
        _parse(_TermPartyRow, r, path=term_parties_path, line=i + 2)
        for i, r in enumerate(_rows(term_parties_path))
    ]
    by_term: dict[tuple[str, date], list[TermParty]] = {}
    for party_row in party_rows:
        by_term.setdefault((party_row.territory_id, party_row.valid_from), []).append(
            TermParty(party_row.party_id, party_row.role, party_row.source_url)
        )
    terms: list[GovernmentTerm] = []
    for index, raw in enumerate(_rows(terms_path)):
        term_row = _parse(_TermRow, raw, path=terms_path, line=index + 2)
        terms.append(
            GovernmentTerm(
                territory_id=term_row.territory_id,
                president_name=term_row.president_name,
                valid_from=term_row.valid_from,
                valid_to=term_row.valid_to,
                parties=tuple(by_term.pop((term_row.territory_id, term_row.valid_from), [])),
                is_caretaker=term_row.is_caretaker,
                source_url=term_row.source_url,
            )
        )
    if by_term:
        orphans = ", ".join(f"{t} from {d}" for t, d in sorted(by_term))
        raise InvalidGovernmentsFileError(
            f"{term_parties_path.name}: party rows without a term: {orphans}"
        )
    return terms


def _check_unique(values: list[str], *, what: str, path: Path) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise InvalidGovernmentsFileError(f"{path.name}: duplicate {what} {value}")
        seen.add(value)
