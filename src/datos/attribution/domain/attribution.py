"""Who is responsible for what an article describes (ADR-0005, ADR-0014).

Pure: the article's community, sector, named government levels and date, with the competence
table and the government terms, give one entry per named level. Nothing here reads a party, an
outlet or the clock: the same path for every party.
"""

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from datos.governments.application.published import (
    Competence,
    CompetenceLevel,
    GovernmentTerm,
    applicable_competences,
    in_force_on,
)

STATE_TERRITORY_ID = "es"  # the anchor of the State's terms (ADR-0011)


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"  # unused while no managing level is curated (ADR-0014, D6 = A)
    NOT_DETERMINED = "not_determined"


class Reason(StrEnum):
    NO_LEVEL_NAMED = "no_level_named"  # the sector's competences are shared by several levels
    NO_COMPETENCE = "no_competence"  # the named level holds no competence of the sector there
    LOCAL_NOT_MODELLED = "local_not_modelled"
    NO_GOVERNMENT_ON_DATE = "no_government_on_date"


@dataclass(frozen=True, slots=True)
class AttributionEntry:
    level: CompetenceLevel | None  # None when the article names no level
    territory_id: str | None  # whose government: "es", "ccaa-NN", or None
    confidence: Confidence
    party_ids: tuple[str, ...]  # governing parties on the date, alphabetical; empty unless high
    is_caretaker: bool
    competences: tuple[Competence, ...]  # why that level is responsible
    reason: Reason | None  # set exactly when not determined


# Entries come in this order whatever the order the levels were detected in.
_LEVEL_ORDER = (CompetenceLevel.STATE, CompetenceLevel.CCAA, CompetenceLevel.LOCAL)


def attribute(
    *,
    community_id: str,
    sector_id: str,
    levels: Collection[CompetenceLevel],
    published_on: date,
    terms: Sequence[GovernmentTerm],
    competences: Sequence[Competence],
) -> list[AttributionEntry]:
    """One entry per named level; a single not-determined entry when none is named."""
    if not levels:
        return [_not_determined(None, None, Reason.NO_LEVEL_NAMED)]
    sector_rows = _sector_competences(competences, sector_id=sector_id, community_id=community_id)
    return [
        _entry(level, community_id, published_on, terms, sector_rows)
        for level in _LEVEL_ORDER
        if level in levels
    ]


def _entry(
    level: CompetenceLevel,
    community_id: str,
    published_on: date,
    terms: Sequence[GovernmentTerm],
    sector_rows: Sequence[Competence],
) -> AttributionEntry:
    if level is CompetenceLevel.LOCAL:
        return _not_determined(level, None, Reason.LOCAL_NOT_MODELLED)
    territory_id = STATE_TERRITORY_ID if level is CompetenceLevel.STATE else community_id
    held = tuple(c for c in sector_rows if c.level is level)
    if not held:
        return _not_determined(level, territory_id, Reason.NO_COMPETENCE)
    term = in_force_on(terms, territory_id, published_on)
    if term is None:
        return _not_determined(level, territory_id, Reason.NO_GOVERNMENT_ON_DATE)
    return AttributionEntry(
        level=level,
        territory_id=territory_id,
        confidence=Confidence.HIGH,
        party_ids=tuple(sorted(term.governing_party_ids)),  # never the parties that only supported
        is_caretaker=term.is_caretaker,
        competences=held,
        reason=None,
    )


def _sector_competences(
    competences: Sequence[Competence], *, sector_id: str, community_id: str
) -> list[Competence]:
    """The rows of the sector that apply in the community: per activity, its own rows replace
    the general ones (Ceuta and Melilla)."""
    activities = sorted({c.activity for c in competences if c.sector_id == sector_id})
    return [
        row
        for activity in activities
        for row in applicable_competences(
            competences, sector_id=sector_id, activity=activity, territory_id=community_id
        )
    ]


def _not_determined(
    level: CompetenceLevel | None, territory_id: str | None, reason: Reason
) -> AttributionEntry:
    return AttributionEntry(
        level=level,
        territory_id=territory_id,
        confidence=Confidence.NOT_DETERMINED,
        party_ids=(),
        is_caretaker=False,
        competences=(),
        reason=reason,
    )
