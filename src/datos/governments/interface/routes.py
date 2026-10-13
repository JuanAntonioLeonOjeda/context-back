"""Governments API: the government of a community on a date, and the party table."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from datos.api.provider import Provider
from datos.clock import Clock
from datos.governments.application.read_governments import GovernmentsReader, government_on
from datos.governments.domain.government_term import GovernmentTerm, PartyRole
from datos.territories.routes import TerritoryReader
from datos.territories.territory import Level


class TermPartyOut(BaseModel):
    party_id: str
    short_name: str
    role: PartyRole
    source_url: str


class TermOut(BaseModel):
    president_name: str
    valid_from: date
    is_caretaker: bool
    source_url: str
    parties: list[TermPartyOut]


class GovernmentOut(BaseModel):
    territory_id: str
    date: date
    term: TermOut


class PartyOut(BaseModel):
    id: str
    name: str
    short_name: str
    colour_hex: str


def build_governments_router(
    governments: Provider[GovernmentsReader],
    territories: Provider[TerritoryReader],
    clock: Clock,
) -> APIRouter:
    router = APIRouter(tags=["governments"])

    @router.get("/communities/{territory_id}/governments", response_model=GovernmentOut)
    def government(
        territory_id: str,
        reader: Annotated[GovernmentsReader, Depends(governments)],
        territory_reader: Annotated[TerritoryReader, Depends(territories)],
        on: Annotated[date | None, Query(alias="date")] = None,
    ) -> GovernmentOut:
        if territory_id not in {t.id for t in territory_reader.by_level(Level.CCAA)}:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown community {territory_id}")
        day = on or clock.today()
        term = government_on(reader, territory_id, day)
        if term is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                f"no government of {territory_id} in the dataset on {day}",
            )
        names = {p.id: p.short_name for p in reader.parties()}
        return GovernmentOut(territory_id=territory_id, date=day, term=_term_out(term, names))

    @router.get("/parties", response_model=list[PartyOut])
    def parties(reader: Annotated[GovernmentsReader, Depends(governments)]) -> list[PartyOut]:
        return [
            PartyOut(id=p.id, name=p.name, short_name=p.short_name, colour_hex=p.colour_hex)
            for p in reader.parties()
        ]

    return router


def _term_out(term: GovernmentTerm, short_names: dict[str, str]) -> TermOut:
    return TermOut(
        president_name=term.president_name,
        valid_from=term.valid_from,
        is_caretaker=term.is_caretaker,
        source_url=term.source_url,
        # Alphabetical by id: the order never depends on a party's size or role.
        parties=[
            TermPartyOut(
                party_id=p.party_id,
                short_name=short_names[p.party_id],
                role=p.role,
                source_url=p.source_url,
            )
            for p in sorted(term.parties, key=lambda p: p.party_id)
        ],
    )
