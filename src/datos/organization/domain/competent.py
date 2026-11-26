"""The bodies with competence in what a news item is about (ADR-0027).

A news item is attributed to the body that holds the competence, never to a person or a party: what
comes out is a fact of the body, with the sector it was reached by and whether the level of
government was the news item's own or the competence table's. Pure: the news item's
classification, the bodies, their competences and the levels the table gives each sector come in
as parameters, and the day is the news item's publication day, never the clock.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date

from datos.organization.domain.body import Body, BodyKind, BodyLevel
from datos.organization.domain.boxes import Competence

STATE_TERRITORY = "es"
# Only a department (a consejería, a ministry) or a local body manages a matter: the head of an
# executive, a parliament or a court hold competences of another kind, and are never shown here.
MANAGING_KINDS = frozenset({BodyKind.DEPARTMENT, BodyKind.LOCAL})
LEVEL_ORDER = (BodyLevel.STATE, BodyLevel.CCAA, BodyLevel.LOCAL)


@dataclass(frozen=True, slots=True)
class NewsTopic:
    """What the active classifier said of a news item, and the day it was published."""

    communities: frozenset[str]  # territory ids: "ccaa-05"
    sectors: frozenset[str]
    # Often empty: the rules give a level only when the text names an institution.
    levels: frozenset[BodyLevel]
    published_on: date


@dataclass(frozen=True, slots=True)
class CompetentBody:
    body: Body
    sector_id: str  # the sector of the news item that led to the body
    shared: bool  # True: the news item had no level, the competence table's levels were used


def competent_bodies(
    topic: NewsTopic,
    bodies: Iterable[Body],
    competences: Iterable[Competence],
    table_levels: Mapping[str, frozenset[BodyLevel]],
) -> list[CompetentBody]:
    """The bodies in force on the publication day whose competences carry a sector of the news item,
    at its levels; by sector, then level (State, community, local), then name."""
    sectors_of = _sectors_by_body(competences)
    candidates = [
        b for b in bodies if b.kind in MANAGING_KINDS and b.in_force_on(topic.published_on)
    ]
    found: list[CompetentBody] = []
    for sector_id in sorted(topic.sectors):
        levels, shared = levels_for(sector_id, topic, table_levels)
        found.extend(
            CompetentBody(body, sector_id, shared)
            for body in sorted(candidates, key=_order)
            if sector_id in sectors_of.get(body.id, frozenset())
            and body.level in levels
            and _reaches(body, topic)
        )
    return found


def levels_for(
    sector_id: str, topic: NewsTopic, table_levels: Mapping[str, frozenset[BodyLevel]]
) -> tuple[frozenset[BodyLevel], bool]:
    """The news item's own levels; when it has none, the State's and the community's of those the
    competence table gives the sector, said to be shared (True). The local level only when the
    news item says so: the table gives it to most sectors (health, schooling, planning), and the
    ayuntamiento would be named on almost every news item. A sector the table does not know gives
    no level."""
    if topic.levels:
        return topic.levels, False
    return table_levels.get(sector_id, frozenset()) - {BodyLevel.LOCAL}, True


def _reaches(body: Body, topic: NewsTopic) -> bool:
    """By the body's territory, not its level: the State's bodies and the generic local ones (no
    territory) reach any news item; a body of one community (a consejería, or a local body that
    only exists there, like a Canarian cabildo) only a news item of that community."""
    return body.territory_id in (None, STATE_TERRITORY) or body.territory_id in topic.communities


def _sectors_by_body(competences: Iterable[Competence]) -> dict[str, frozenset[str]]:
    sectors: dict[str, set[str]] = {}
    for competence in competences:
        sectors.setdefault(competence.body_id, set()).update(competence.sector_ids)
    return {body_id: frozenset(ids) for body_id, ids in sectors.items()}


def _order(body: Body) -> tuple[int, str]:
    return LEVEL_ORDER.index(body.level), body.name
