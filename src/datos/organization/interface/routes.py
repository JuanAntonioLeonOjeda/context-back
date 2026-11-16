"""`GET /organization` and `GET /communities/{id}/organization`: the organisation chart.

Bodies, the holder of the head post of each executive and department, and the competences the law
gives each body, every one with its source. It says nothing about who is responsible for what a
news item says, and never gives a party (ADR-0025). The executive is complete or nothing: if any
of its holders is missing, its status is `no_data` and nothing of it is returned.
"""

from collections.abc import Mapping
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from datos.api.provider import Provider
from datos.clock import Clock
from datos.organization.application.organization_chart import (
    OrganizationChart,
    OrganizationReader,
    general_chart,
    organization_chart,
)
from datos.organization.domain.body import Body, Holder
from datos.organization.domain.boxes import Box, Competence
from datos.organization.domain.chart import Post
from datos.territories.routes import TerritoryReader
from datos.territories.territory import Level

STATE = "es"

DESCRIPTION = """The bodies of a territory with what the law gives each of them, and who holds the
head post of its executive and of each department (the president or prime minister, the
consejeros or ministers) on the day of the answer, each row with its source.

`executive.status` is `complete` only if the head and every department have a holder in force that
day; otherwise it is `no_data`, with no head and no departments: the web app says "sin datos
todavía". Departments are ordered by name, never by importance. No party is given for anyone."""


class SectorRefOut(BaseModel):
    id: str
    name: str


class CompetenceOut(BaseModel):
    summary: str  # in the project's own words
    legal_basis: str  # the article
    sectors: list[SectorRefOut]
    source_url: str


class HolderOut(BaseModel):
    name: str
    post_title: str  # as the appointment writes it
    since: date  # the date of the decree that gave the post under that title
    source_url: str


class BodyOut(BaseModel):
    id: str
    name: str  # the official name
    kind: Literal["executive_head", "department", "parliament", "judiciary", "local"]
    level: Literal["state", "ccaa", "local"]
    dir3_id: str | None
    source_url: str
    holder: HolderOut | None  # only the head of an executive and a department have one
    competences: list[CompetenceOut]


class ExecutiveOut(BaseModel):
    status: Literal["complete", "no_data"]
    head: BodyOut | None
    departments: list[BodyOut]


class OrganizationOut(BaseModel):
    territory_id: str  # "es" for the general chart
    as_of: date
    executive: ExecutiveOut
    parliaments: list[BodyOut]
    judiciary: list[BodyOut]  # the State's, or the court that sits in the community
    local: list[BodyOut]  # generic ones and those that exist in the community only


class CommunityRefOut(BaseModel):
    territory_id: str
    name: str
    executive_status: Literal["complete", "no_data"]


class GeneralOrganizationOut(OrganizationOut):
    communities: list[CommunityRefOut]  # by name, with whether their executive can be drawn


class NotFoundOut(BaseModel):
    detail: str


def build_organization_router(
    organization: Provider[OrganizationReader],
    territories: Provider[TerritoryReader],
    clock: Clock,
) -> APIRouter:
    router = APIRouter(tags=["organization"])

    @router.get("/organization", response_model=GeneralOrganizationOut, description=DESCRIPTION)
    def general(
        reader: Annotated[OrganizationReader, Depends(organization)],
        territory_reader: Annotated[TerritoryReader, Depends(territories)],
    ) -> GeneralOrganizationOut:
        day = clock.today()
        communities = sorted(
            territory_reader.by_level(Level.CCAA), key=lambda t: (t.name.casefold(), t.id)
        )
        state_chart, statuses = general_chart(reader, [t.id for t in communities], day)
        chart = _out(state_chart)
        return GeneralOrganizationOut(
            **chart.model_dump(),
            communities=[
                CommunityRefOut(
                    territory_id=t.id, name=t.name, executive_status=statuses[t.id].value
                )
                for t in communities
            ],
        )

    @router.get(
        "/communities/{territory_id}/organization",
        response_model=OrganizationOut,
        description=DESCRIPTION,
        responses={status.HTTP_404_NOT_FOUND: {"model": NotFoundOut}},
    )
    def community(
        territory_id: str,
        reader: Annotated[OrganizationReader, Depends(organization)],
        territory_reader: Annotated[TerritoryReader, Depends(territories)],
    ) -> OrganizationOut:
        if territory_id not in {t.id for t in territory_reader.by_level(Level.CCAA)}:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown community {territory_id}")
        return _out(organization_chart(reader, territory_id, clock.today()))

    return router


def _out(chart: OrganizationChart) -> OrganizationOut:
    names = chart.sector_names
    head = chart.executive.head
    return OrganizationOut(
        territory_id=chart.territory_id,
        as_of=chart.day,
        executive=ExecutiveOut(
            status=chart.executive.status.value,
            head=None if head is None else _post(head, chart.executive_competences, names),
            departments=[
                _post(p, chart.executive_competences, names) for p in chart.executive.departments
            ],
        ),
        parliaments=[_box(b, names) for b in chart.parliaments],
        judiciary=[_box(b, names) for b in chart.judiciary],
        local=[_box(b, names) for b in chart.local],
    )


def _post(
    post: Post, competences: Mapping[str, tuple[Competence, ...]], names: Mapping[str, str]
) -> BodyOut:
    return _body(post.body, post.holder, competences.get(post.body.id, ()), names)


def _box(box: Box, names: Mapping[str, str]) -> BodyOut:
    return _body(box.body, None, box.competences, names)


def _body(
    body: Body, holder: Holder | None, competences: tuple[Competence, ...], names: Mapping[str, str]
) -> BodyOut:
    return BodyOut(
        id=body.id,
        name=body.name,
        kind=body.kind.value,
        level=body.level.value,
        dir3_id=body.dir3_id,
        source_url=body.source_url,
        holder=None if holder is None else _holder(holder),
        competences=[_competence(c, names) for c in competences],
    )


def _holder(holder: Holder) -> HolderOut:
    return HolderOut(
        name=holder.holder_name,
        post_title=holder.post_title,
        since=holder.valid_from,
        source_url=holder.source_url,
    )


def _competence(competence: Competence, names: Mapping[str, str]) -> CompetenceOut:
    return CompetenceOut(
        summary=competence.summary,
        legal_basis=competence.legal_basis,
        sectors=[SectorRefOut(id=s, name=names.get(s, s)) for s in competence.sector_ids],
        source_url=competence.source_url,
    )
