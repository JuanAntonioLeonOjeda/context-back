"""Bodies of the State and the communities, and who holds their head post on a given day.

A body is a box of the organisation chart. Only the head of an executive and a department have
a holder (the president, a consejero, a minister); a parliament, a court or a local body has none.
Pure functions only: "today" is a parameter, never read from the clock. Periods are half-open
[valid_from, valid_to), so the day of a change belongs to the new holder; `valid_to` None means the
holder is in force.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class BodyKind(StrEnum):
    EXECUTIVE_HEAD = "executive_head"
    DEPARTMENT = "department"  # a consejería or a ministry
    PARLIAMENT = "parliament"
    JUDICIARY = "judiciary"
    LOCAL = "local"


class BodyLevel(StrEnum):
    STATE = "state"
    CCAA = "ccaa"
    LOCAL = "local"


# The only kinds of body with a holder; the database refuses a holder on any other.
HEADED_KINDS = frozenset({BodyKind.EXECUTIVE_HEAD, BodyKind.DEPARTMENT})


@dataclass(frozen=True, slots=True)
class Body:
    id: str  # starts with its territory id: "ccaa-13-sanidad"; "local-…" for a generic local body
    kind: BodyKind
    level: BodyLevel
    territory_id: str | None  # None only for a generic local body
    name: str  # the official name
    parent_id: str | None  # a department's parent is the executive head of its territory
    dir3_id: str | None  # the code of the body in DIR3, to cross-check names
    source_url: str

    @property
    def has_holder(self) -> bool:
        return self.kind in HEADED_KINDS


@dataclass(frozen=True, slots=True)
class Holder:
    body_id: str
    post_title: str  # as the appointment writes it: "Vicepresidente primero y Ministro de Hacienda"
    holder_name: str
    valid_from: date
    valid_to: date | None
    source_url: str

    def covers(self, day: date) -> bool:
        return self.valid_from <= day and (self.valid_to is None or day < self.valid_to)


def holder_on(holders: Iterable[Holder], body_id: str, day: date) -> Holder | None:
    """The holder of the head post of `body_id` on `day`, if any.

    Assumes no overlaps for one body (checked by the loader and by the database).
    """
    return next((h for h in holders if h.body_id == body_id and h.covers(day)), None)
