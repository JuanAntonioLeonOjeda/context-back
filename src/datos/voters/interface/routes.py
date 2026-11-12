"""`GET /communities/{id}/voters`: how a community's municipalities voted, by income band.

Every number is computed here, from the stored results, and rounded for display; the web app
only draws it. Parties are ordered by the name shown, never by size; "Otras" goes last.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from datos.api.provider import Provider
from datos.governments.application.read_governments import GovernmentsReader
from datos.territories.routes import TerritoryReader
from datos.territories.territory import Level
from datos.voters.application.community_voters import (
    CommunityVoters,
    PartyByCandidature,
    VotersReader,
    community_voters,
)
from datos.voters.domain.profile import (
    LIST_PREFIX,
    OTHERS,
    SHOWN_FROM_PERCENT,
    Band,
    VoterProfile,
)

INFOELECTORAL_URL = (
    "https://infoelectoral.interior.gob.es/es/elecciones-celebradas/area-de-descargas/"
)
# The statistic's page at the INE (Atlas de distribución de renta de los hogares): where a reader
# can check a figure. The request the loader made is a filter of the whole operation that takes
# minutes to answer; it stays in `downloads`, not in the answer.
INE_INCOME_URL = (
    "https://www.ine.es/dyngs/INEbase/es/operacion.htm"
    "?c=Estadistica_C&cid=1254736177088&menu=ultiDatos&idp=1254735976608"
)

DESCRIPTION = """How the municipalities of a community voted in a general election, grouped in
five income bands of about the same census (each municipality whole, in the band where the
midpoint of its census falls; a big city can leave a band almost empty). Income: the INE's mean net
income per person of the election's year. It describes areas, not people.

Without `election`, the latest loaded one. Groups: the parties with at least
`shown_from_percent` % of the community's valid votes (and a candidature that is not in the party
table, by its acronym), then "others". `profile` is null when fewer than two municipalities have
income (Ceuta, Melilla). 404: the community does not exist, or no such election is loaded."""


class ElectionOut(BaseModel):
    id: str
    held_on: date
    source_file: str
    source_url: str


class IncomeOut(BaseModel):
    year: int
    source_url: str  # the statistic's page at the INE
    fetched_at: datetime


class GroupOut(BaseModel):
    id: str
    # "candidature": one that is not in the party table, shown by its acronym from the file.
    kind: Literal["party", "candidature", "others"]
    # The party's short name, or the candidature's acronym; null for "others".
    label: str | None


class ShareOut(BaseModel):
    group_id: str
    votes: int
    percent: float  # of the band's valid votes, one decimal


class BandOut(BaseModel):
    index: int  # 0 = the lowest incomes
    municipalities: int
    census: int
    census_percent: float  # of the profile's census, one decimal
    income_min_eur: float | None
    income_max_eur: float | None
    valid_votes: int
    blank_votes: int
    blank_percent: float
    shares: list[ShareOut]  # in the order of `groups`


class ProfileOut(BaseModel):
    census: int
    groups: list[GroupOut]
    bands: list[BandOut]
    municipalities_without_income: int


class VotersOut(BaseModel):
    territory_id: str
    election: ElectionOut
    income: IncomeOut | None
    municipalities: int
    # A group is shown from this percentage of the community's valid votes; the rest is "others".
    shown_from_percent: int
    profile: ProfileOut | None
    no_profile_reason: Literal["no_results", "too_few_municipalities"] | None


class NotFoundOut(BaseModel):
    detail: str


def build_voters_router(
    voters: Provider[VotersReader],
    governments: Provider[GovernmentsReader],
    territories: Provider[TerritoryReader],
    party_by_candidature: PartyByCandidature,
) -> APIRouter:
    router = APIRouter(tags=["voters"])

    @router.get(
        "/communities/{territory_id}/voters",
        response_model=VotersOut,
        description=DESCRIPTION,
        responses={status.HTTP_404_NOT_FOUND: {"model": NotFoundOut}},
    )
    def community(
        territory_id: str,
        reader: Annotated[VotersReader, Depends(voters)],
        governments_reader: Annotated[GovernmentsReader, Depends(governments)],
        territory_reader: Annotated[TerritoryReader, Depends(territories)],
        election: Annotated[str | None, Query(description="e.g. congreso-2023-07")] = None,
    ) -> VotersOut:
        if territory_id not in {t.id for t in territory_reader.by_level(Level.CCAA)}:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown community {territory_id}")
        found = community_voters(
            reader, party_by_candidature, territory_id=territory_id, election_id=election
        )
        if found is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"no election {election or 'loaded'}")
        labels = {p.id: p.short_name for p in governments_reader.parties()}
        return _out(territory_id, found, labels)

    return router


def _out(territory_id: str, found: CommunityVoters, labels: dict[str, str]) -> VotersOut:
    e = found.election
    reason: Literal["no_results", "too_few_municipalities"] | None = None
    if found.profile is None:
        reason = "no_results" if found.municipalities == 0 else "too_few_municipalities"
    return VotersOut(
        territory_id=territory_id,
        election=ElectionOut(
            id=e.id, held_on=e.held_on, source_file=e.source_file, source_url=INFOELECTORAL_URL
        ),
        income=None
        if found.income is None
        else IncomeOut(
            year=found.income.year, source_url=INE_INCOME_URL, fetched_at=found.income.fetched_at
        ),
        municipalities=found.municipalities,
        shown_from_percent=SHOWN_FROM_PERCENT,
        profile=None if found.profile is None else _profile(found.profile, labels),
        no_profile_reason=reason,
    )


def _profile(profile: VoterProfile, labels: dict[str, str]) -> ProfileOut:
    groups = _groups(profile, labels)
    return ProfileOut(
        census=profile.census,
        groups=groups,
        bands=[_band(b, profile.census, groups) for b in profile.bands],
        municipalities_without_income=len(profile.without_income),
    )


def _groups(profile: VoterProfile, labels: dict[str, str]) -> list[GroupOut]:
    """The shown groups ordered by the label a reader sees, case-insensitively; others last."""
    shown = [_group(g, labels) for g in profile.shown_groups]
    ordered = sorted(shown, key=lambda g: ((g.label or "").casefold(), g.id))
    return [*ordered, GroupOut(id=OTHERS, kind="others", label=None)]


def _group(group_id: str, labels: dict[str, str]) -> GroupOut:
    if group_id.startswith(LIST_PREFIX):
        return GroupOut(id=group_id, kind="candidature", label=group_id.removeprefix(LIST_PREFIX))
    return GroupOut(id=group_id, kind="party", label=labels.get(group_id, group_id))


def _band(band: Band, census: int, groups: list[GroupOut]) -> BandOut:
    return BandOut(
        index=band.index,
        municipalities=len(band.municipality_codes),
        census=band.census,
        census_percent=_percent(band.census, census),
        income_min_eur=_euros(band.income_min),
        income_max_eur=_euros(band.income_max),
        valid_votes=band.valid_votes,
        blank_votes=band.blank_votes,
        blank_percent=_percent(band.blank_votes, band.valid_votes),
        shares=[
            ShareOut(
                group_id=g.id,
                votes=band.votes.get(g.id, 0),
                percent=_percent(band.votes.get(g.id, 0), band.valid_votes),
            )
            for g in groups
        ],
    )


def _percent(part: int, whole: int) -> float:
    """One decimal, half up; 0 when the whole is 0 (an empty band)."""
    if whole == 0:
        return 0.0
    return float((Decimal(100 * part) / Decimal(whole)).quantize(Decimal("0.1"), "ROUND_HALF_UP"))


def _euros(value: Decimal | None) -> float | None:
    return None if value is None else float(value)
