"""An election's official results by municipality, as the Ministerio del Interior publishes them."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class ElectionKind(StrEnum):
    """The elections this project loads (spec decision 1: general elections only)."""

    CONGRESO = "congreso"


@dataclass(frozen=True, slots=True)
class Election:
    kind: ElectionKind
    held_on: date

    @property
    def id(self) -> str:
        """`congreso-2023-07`: the kind and the month, as the Ministerio names its files."""
        return f"{self.kind}-{self.held_on:%Y-%m}"


@dataclass(frozen=True, slots=True)
class Candidature:
    code: str
    acronym: str
    name: str
    # The candidature its votes add up to nationally (PSC → PSOE); a head is its own.
    national_head_code: str


@dataclass(frozen=True, slots=True)
class MunicipalResult:
    municipality_code: str  # INE: province (2) + municipality (3)
    municipality_name: str
    census: int  # INE census of the municipality
    blank_votes: int
    null_votes: int
    candidature_votes: int

    @property
    def valid_votes(self) -> int:
        """Spanish electoral law counts blank votes as valid; null votes are not."""
        return self.blank_votes + self.candidature_votes


@dataclass(frozen=True, slots=True)
class CandidatureVotes:
    municipality_code: str
    candidature_code: str
    votes: int


@dataclass(frozen=True, slots=True)
class ElectionFile:
    """Everything one downloaded file says, before it is checked or stored."""

    source_file: str
    sha256: str
    election: Election
    candidatures: tuple[Candidature, ...]
    results: tuple[MunicipalResult, ...]
    votes: tuple[CandidatureVotes, ...]
