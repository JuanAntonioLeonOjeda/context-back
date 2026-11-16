"""Read side of voters: the voter profile of a community for an election (spec AC3)."""

from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol

from datos.voters.domain.dimensions import INCOME, Dimension, DimensionId
from datos.voters.domain.profile import MunicipalVotes, VoterProfile, vote_group, voter_profile


@dataclass(frozen=True, slots=True)
class ElectionInfo:
    id: str
    held_on: date
    source_file: str


@dataclass(frozen=True, slots=True)
class IncomeDownloadInfo:
    year: int
    url: str
    fetched_at: datetime


@dataclass(frozen=True, slots=True)
class CandidatureCount:
    """A candidature's votes in a municipality, with its code and acronym from file 03."""

    code: str
    acronym: str
    votes: int


@dataclass(frozen=True, slots=True)
class MunicipalRow:
    code: str
    census: int
    blank_votes: int
    income: Decimal | None
    counts: Sequence[CandidatureCount]


class VotersReader(Protocol):
    def elections(self) -> list[ElectionInfo]:
        """Every loaded election, the latest first."""
        ...

    def municipal_rows(
        self, territory_id: str, election_id: str, income_year: int
    ) -> list[MunicipalRow]:
        """The community's municipalities in that election, each with its latest income."""
        ...

    def income_download(self, year: int) -> IncomeDownloadInfo | None:
        """The latest INE download of income for the year, to name the source."""
        ...


@dataclass(frozen=True, slots=True)
class CommunityVoters:
    election: ElectionInfo
    dimension: Dimension
    # The INE download the dimension's values come from; None when they come from the election's
    # own files (the size of a municipality is its census).
    download: IncomeDownloadInfo | None
    municipalities: int
    profile: VoterProfile | None  # None: fewer than two municipalities with a value


# The curated table: election id → candidature code → party id (data/voters/).
type PartyByCandidature = Mapping[str, Mapping[str, str]]

# How each dimension reads the value of a municipality from its row (None: no value).
_VALUE_OF: dict[DimensionId, Callable[[MunicipalRow], Decimal | None]] = {
    DimensionId.INCOME: lambda row: row.income,
    DimensionId.SIZE: lambda row: Decimal(row.census),
}


def community_voters(
    reader: VotersReader,
    party_by_candidature: PartyByCandidature,
    *,
    territory_id: str,
    election_id: str | None,
    dimension: Dimension = INCOME,
) -> CommunityVoters | None:
    """The profile by `dimension` for `election_id`, or for the latest loaded election when it is
    None; None when there is no such election."""
    elections = reader.elections()
    election = next((e for e in elections if election_id in (None, e.id)), None)
    if election is None:
        return None
    # Spec decision 8: the income of the election's year describes the municipalities as they
    # were when they voted.
    year = election.held_on.year
    rows = reader.municipal_rows(territory_id, election.id, year)
    parties = party_by_candidature.get(election.id, {})
    value_of = _VALUE_OF[dimension.id]
    municipalities = [_municipal_votes(row, parties, value_of(row)) for row in rows]
    return CommunityVoters(
        election=election,
        dimension=dimension,
        download=reader.income_download(year) if dimension.id is DimensionId.INCOME else None,
        municipalities=len(rows),
        profile=voter_profile(municipalities, dimension.grouping),
    )


def _municipal_votes(
    row: MunicipalRow, parties: Mapping[str, str], value: Decimal | None
) -> MunicipalVotes:
    votes: dict[str, int] = defaultdict(int)
    for count in row.counts:
        votes[vote_group(count.code, count.acronym, parties)] += count.votes
    return MunicipalVotes(row.code, row.census, value, row.blank_votes, dict(votes))
