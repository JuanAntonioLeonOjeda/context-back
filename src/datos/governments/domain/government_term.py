"""Government terms and the rules that make "who governed on day X" well defined.

Pure functions only: "today" is a parameter, never read from the clock.
Periods are half-open [valid_from, valid_to); valid_to None means in force.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class PartyRole(StrEnum):
    GOVERNING = "governing"
    EXTERNAL_SUPPORT = "external_support"


@dataclass(frozen=True, slots=True)
class TermParty:
    party_id: str
    role: PartyRole
    source_url: str  # the evidence for this party's role in this term


@dataclass(frozen=True, slots=True)
class GovernmentTerm:
    territory_id: str
    president_name: str
    valid_from: date
    valid_to: date | None
    parties: tuple[TermParty, ...]
    is_caretaker: bool
    source_url: str

    @property
    def governing_party_ids(self) -> tuple[str, ...]:
        return tuple(p.party_id for p in self.parties if p.role is PartyRole.GOVERNING)

    @property
    def is_coalition(self) -> bool:
        return len(self.governing_party_ids) >= 2

    @property
    def has_external_support(self) -> bool:
        return any(p.role is PartyRole.EXTERNAL_SUPPORT for p in self.parties)

    def covers(self, day: date) -> bool:
        return self.valid_from <= day and (self.valid_to is None or day < self.valid_to)


# --- problems ------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class NoGoverningParty:
    term: GovernmentTerm


@dataclass(frozen=True, slots=True)
class EmptyPeriod:
    term: GovernmentTerm


@dataclass(frozen=True, slots=True)
class Overlap:
    first: GovernmentTerm
    second: GovernmentTerm


@dataclass(frozen=True, slots=True)
class Gap:
    """Days without a government: [start, end), end None meaning "until today and on"."""

    territory_id: str
    start: date
    end: date | None


TermProblem = NoGoverningParty | EmptyPeriod
TimelineProblem = Overlap | Gap


def term_problems(term: GovernmentTerm) -> list[TermProblem]:
    """Problems of one term on its own (the rules a single-row CHECK cannot express)."""
    problems: list[TermProblem] = []
    if not term.governing_party_ids:
        problems.append(NoGoverningParty(term))
    if term.valid_to is not None and term.valid_to <= term.valid_from:
        problems.append(EmptyPeriod(term))
    return problems


def timeline_problems(
    terms: Iterable[GovernmentTerm],
    territory_ids: Iterable[str],
    *,
    since: date,
    today: date,
) -> list[TimelineProblem]:
    """Overlaps and gaps from `since` to `today` for each listed territory."""
    by_territory: dict[str, list[GovernmentTerm]] = {}
    for term in terms:
        by_territory.setdefault(term.territory_id, []).append(term)
    problems: list[TimelineProblem] = []
    for territory_id in territory_ids:
        ordered = sorted(by_territory.get(territory_id, []), key=lambda t: t.valid_from)
        problems.extend(_territory_problems(territory_id, ordered, since=since, today=today))
    return problems


def _territory_problems(
    territory_id: str, ordered: Sequence[GovernmentTerm], *, since: date, today: date
) -> list[TimelineProblem]:
    if not ordered:
        return [Gap(territory_id, since, None)]
    problems: list[TimelineProblem] = []
    if ordered[0].valid_from > since:
        problems.append(Gap(territory_id, since, ordered[0].valid_from))
    # Compare each term with the one reaching furthest so far, not only with the previous
    # one: a long term can overlap several later terms and hide what looks like a gap.
    furthest = ordered[0]
    for current in ordered[1:]:
        problems.extend(_between(furthest, current))
        if _ends_later(current, furthest):
            furthest = current
    if furthest.valid_to is not None and furthest.valid_to <= today:
        problems.append(Gap(territory_id, furthest.valid_to, None))
    return problems


def _between(furthest: GovernmentTerm, current: GovernmentTerm) -> list[TimelineProblem]:
    end = furthest.valid_to
    if end is None or end > current.valid_from:
        return [Overlap(furthest, current)]
    if end < current.valid_from:
        return [Gap(current.territory_id, end, current.valid_from)]
    return []


def _ends_later(term: GovernmentTerm, other: GovernmentTerm) -> bool:
    if term.valid_to is None:
        return other.valid_to is not None
    return other.valid_to is not None and term.valid_to > other.valid_to


def in_force_on(
    terms: Iterable[GovernmentTerm], territory_id: str, day: date
) -> GovernmentTerm | None:
    """The term governing `territory_id` on `day`, if any.

    Assumes no overlaps (checked by `timeline_problems` and by the database).
    """
    return next((t for t in terms if t.territory_id == territory_id and t.covers(day)), None)
