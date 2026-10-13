"""Competences: which level of government does what, per sector and activity.

A row without territory applies to every community. Rows for one community replace the
general rows of the same sector and activity there (Ceuta and Melilla do not manage
education or health care).
"""

from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum


class CompetenceLevel(StrEnum):
    STATE = "state"
    CCAA = "ccaa"
    LOCAL = "local"


class CompetenceFunction(StrEnum):
    LEGISLATION = "legislation"
    BASIC_LEGISLATION = "basic_legislation"
    DEVELOPMENT_LEGISLATION = "development_legislation"
    EXECUTION = "execution"


@dataclass(frozen=True, slots=True)
class Sector:
    id: str
    name: str


@dataclass(frozen=True, slots=True)
class Competence:
    sector_id: str
    activity: str
    description: str
    level: CompetenceLevel
    function: CompetenceFunction
    territory_id: str | None
    legal_basis: str
    source_url: str


def applicable_competences(
    competences: Iterable[Competence], *, sector_id: str, activity: str, territory_id: str
) -> list[Competence]:
    """The rows that apply to one activity in one community: its own rows if it has any,
    otherwise the general ones."""
    rows = [c for c in competences if c.sector_id == sector_id and c.activity == activity]
    own = [c for c in rows if c.territory_id == territory_id]
    return own if own else [c for c in rows if c.territory_id is None]


def competence_problems(
    sectors: Sequence[Sector], competences: Sequence[Competence], community_ids: Collection[str]
) -> list[str]:
    """Rules of the competence table, as readable messages (empty when it is valid)."""
    problems: list[str] = []
    sector_ids = {s.id for s in sectors}
    general = {(c.sector_id, c.activity) for c in competences if c.territory_id is None}
    seen: set[tuple[str, str, str, str, str | None]] = set()
    for c in competences:
        where = f"{c.sector_id}/{c.activity}/{c.level}/{c.function}" + (
            f"/{c.territory_id}" if c.territory_id else ""
        )
        key = (c.sector_id, c.activity, c.level.value, c.function.value, c.territory_id)
        if key in seen:
            problems.append(f"{where}: duplicate row")
        seen.add(key)
        if c.sector_id not in sector_ids:
            problems.append(f"{where}: unknown sector")
        if c.territory_id is not None and c.territory_id not in community_ids:
            problems.append(f"{where}: territory is not a community")
        if c.territory_id is not None and (c.sector_id, c.activity) not in general:
            problems.append(f"{where}: territory row without general rows to replace")
        if not c.source_url.startswith("https://"):
            problems.append(f"{where}: source is not an https URL")
    used = {c.sector_id for c in competences}
    problems.extend(f"sector {s.id} has no competences" for s in sectors if s.id not in used)
    return problems
