"""Reader of the curated candidature → party table (data/voters/candidature-parties.csv).

Reference data fails fast: a row that does not validate, or a candidature written twice for
the same election, stops the load with its line, instead of the later row silently winning.
"""

import csv
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from datos.voters.application.community_voters import PartyByCandidature


class InvalidCandidaturePartiesError(Exception):
    """The file is missing or has a row that does not validate or repeats a candidature."""


class _Row(BaseModel):
    election_id: str = Field(pattern=r"^[a-z]+-[0-9]{4}-[0-9]{2}$")  # as in `elections.id`
    candidature_code: str = Field(pattern=r"^[0-9]{6}$")
    acronym_in_file: str = Field(min_length=1)  # for the reader of the file; not used by the code
    party_id: str = Field(min_length=1)


def read_candidature_parties(path: Path) -> PartyByCandidature:
    """election id → candidature code → party id."""
    table: dict[str, dict[str, str]] = {}
    try:
        with path.open(encoding="utf-8", newline="") as file:
            for line, raw in enumerate(csv.DictReader(file), start=2):
                try:
                    row = _Row.model_validate(raw)
                except ValidationError as error:
                    raise InvalidCandidaturePartiesError(f"{path}:{line}: {error}") from error
                parties = table.setdefault(row.election_id, {})
                if row.candidature_code in parties:
                    raise InvalidCandidaturePartiesError(
                        f"{path}:{line}: candidature {row.candidature_code} of"
                        f" {row.election_id} is repeated"
                    )
                parties[row.candidature_code] = row.party_id
    except FileNotFoundError as error:
        raise InvalidCandidaturePartiesError(f"{path}: not found") from error
    return table
