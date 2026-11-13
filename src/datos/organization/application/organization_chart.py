"""Read side: the organisation chart of a territory on a given day (spec AC1 to AC4)."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from datos.organization.domain.body import Body, BodyKind, Holder
from datos.organization.domain.boxes import Box, Competence, boxes, competences_of
from datos.organization.domain.chart import ChartStatus, ExecutiveChart, executive_chart


class OrganizationReader(Protocol):
    def bodies(self) -> list[Body]: ...

    def holders(self) -> list[Holder]: ...

    def competences(self) -> list[Competence]: ...

    def sector_names(self) -> dict[str, str]:
        """The name of every sector of the taxonomy, active or planned, by id."""
        ...


@dataclass(frozen=True, slots=True)
class OrganizationChart:
    territory_id: str  # "es" for the general chart
    day: date
    executive: ExecutiveChart
    # The competences of the head and of each department of the executive, by body id.
    executive_competences: Mapping[str, tuple[Competence, ...]]
    parliaments: tuple[Box, ...]
    judiciary: tuple[Box, ...]
    local: tuple[Box, ...]
    sector_names: Mapping[str, str]


def organization_chart(
    reader: OrganizationReader, territory_id: str, day: date
) -> OrganizationChart:
    """The chart of `territory_id` (`"es"` for the State's and the general one) on `day`.

    The executive is complete or nothing. Parliaments and courts are those of the territory (a TSJ
    sits in its community). The local bodies are the generic ones plus those that exist in that
    territory only: for the State there are none, so the general chart shows the generic ones.
    """
    bodies = reader.bodies()
    competences = reader.competences()
    executive = executive_chart(bodies, reader.holders(), territory_id, day)
    posts = [] if executive.head is None else [executive.head, *executive.departments]
    return OrganizationChart(
        territory_id=territory_id,
        day=day,
        executive=executive,
        executive_competences={p.body.id: competences_of(competences, p.body.id) for p in posts},
        parliaments=boxes(bodies, competences, kind=BodyKind.PARLIAMENT, territory_id=territory_id),
        judiciary=boxes(bodies, competences, kind=BodyKind.JUDICIARY, territory_id=territory_id),
        local=boxes(bodies, competences, kind=BodyKind.LOCAL, territory_id=territory_id),
        sector_names=reader.sector_names(),
    )


def executive_statuses(
    reader: OrganizationReader, territory_ids: Iterable[str], day: date
) -> dict[str, ChartStatus]:
    """Whether each territory's executive can be drawn on `day` (for the list of communities)."""
    bodies = reader.bodies()
    holders = reader.holders()
    return {t: executive_chart(bodies, holders, t, day).status for t in territory_ids}
