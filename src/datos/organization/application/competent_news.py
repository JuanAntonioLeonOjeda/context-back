"""Use case: the bodies with competence in what each news item of a page is about (ADR-0027).

Another module's API: the news read side asks it for each item it answers. The bodies, their
competences and the competence table's levels are read once per request (a few hundred rows) and
the rule of `domain/competent.py` runs for each item; nothing is stored.
"""

from collections.abc import Iterable
from datetime import date
from typing import Protocol

from datos.organization.domain.body import Body, BodyLevel
from datos.organization.domain.boxes import Competence
from datos.organization.domain.competent import CompetentBody, NewsTopic, competent_bodies


class CompetenceReader(Protocol):
    def bodies(self) -> list[Body]: ...

    def competences(self) -> list[Competence]: ...

    def table_levels(self) -> dict[str, frozenset[BodyLevel]]:
        """The levels of government the competence table gives each sector."""
        ...


class CompetentBodies:
    """Built once per request; `of` answers each news item of the page."""

    def __init__(self, reader: CompetenceReader) -> None:
        self._bodies = reader.bodies()
        self._competences = reader.competences()
        self._table_levels = reader.table_levels()

    def of(
        self,
        *,
        communities: Iterable[str],
        sectors: Iterable[str],
        levels: Iterable[str],
        published_on: date,
    ) -> list[CompetentBody]:
        """`levels` are the classifier's ids ("state", "ccaa", "local"), the same as a body's."""
        topic = NewsTopic(
            communities=frozenset(communities),
            sectors=frozenset(sectors),
            levels=frozenset(BodyLevel(level) for level in levels),
            published_on=published_on,
        )
        return competent_bodies(topic, self._bodies, self._competences, self._table_levels)
