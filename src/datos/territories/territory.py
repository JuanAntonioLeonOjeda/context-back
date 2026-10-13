from dataclasses import dataclass
from enum import StrEnum


class Level(StrEnum):
    STATE = "state"
    CCAA = "ccaa"
    PROVINCE = "province"


@dataclass(frozen=True, slots=True)
class Territory:
    id: str
    ine_code: str | None
    name: str
    level: Level
    parent_id: str | None


def parents_first(territories: list[Territory]) -> list[Territory]:
    """Order so every parent is inserted before its children (foreign key on parent_id)."""
    depth = {Level.STATE: 0, Level.CCAA: 1, Level.PROVINCE: 2}
    return sorted(territories, key=lambda territory: (depth[territory.level], territory.id))
