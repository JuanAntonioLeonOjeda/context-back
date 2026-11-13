"""The boxes with no holder (parliaments, courts, local bodies) and the competences of any body.

A box is a body with what the law gives it. Pure functions only. Order never ranks: the boxes come
by name, case-insensitively, with the id to break a tie. The competences of a body keep the order
of the file they are curated in.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from datos.organization.domain.body import HEADED_KINDS, Body, BodyKind


@dataclass(frozen=True, slots=True)
class Competence:
    """What the law gives a body, in the project's own words (ADR-0025: a fact about the body)."""

    body_id: str
    summary: str
    legal_basis: str  # the article: "EA Canarias art. 142"
    sector_ids: tuple[str, ...]
    source_url: str


@dataclass(frozen=True, slots=True)
class Box:
    body: Body
    competences: tuple[Competence, ...]


def competences_of(competences: Iterable[Competence], body_id: str) -> tuple[Competence, ...]:
    """The competences of one body, in the order they were given."""
    return tuple(c for c in competences if c.body_id == body_id)


def boxes(
    bodies: Iterable[Body],
    competences: Iterable[Competence],
    *,
    kind: BodyKind,
    territory_id: str | None,
) -> tuple[Box, ...]:
    """The bodies of `kind` that belong to `territory_id`, each with its competences, by name.

    `territory_id` None gives the generic local bodies, which belong to no territory. For a
    community, local bodies are the generic ones plus those that exist in that community only (a
    cabildo in Canarias). The head of an executive and the departments have a holder and come from
    `executive_chart`, not from here.
    """
    if kind in HEADED_KINDS:
        raise ValueError(f"{kind.value} bodies have a holder: use executive_chart")
    given = list(competences)
    own = [b for b in bodies if _belongs(b, kind, territory_id)]
    ordered = sorted(own, key=lambda b: (b.name.casefold(), b.id))
    return tuple(Box(b, competences_of(given, b.id)) for b in ordered)


def _belongs(body: Body, kind: BodyKind, territory_id: str | None) -> bool:
    if body.kind is not kind:
        return False
    if kind is BodyKind.LOCAL and territory_id is not None:
        return body.territory_id in (None, territory_id)
    return body.territory_id == territory_id
