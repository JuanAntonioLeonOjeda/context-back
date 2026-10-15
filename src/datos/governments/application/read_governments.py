"""Read side of governments: the port the API and attribution use to ask who governed.

The reader returns whole terms; deciding which one is in force on a date stays in the
domain (`in_force_on`), so the rule lives in one place and not also in SQL. The dataset is
small (about a hundred terms), so loading a territory's terms costs nothing.
"""

from datetime import date
from typing import Protocol

from datos.governments.domain.competence import Competence
from datos.governments.domain.government_term import GovernmentTerm, in_force_on
from datos.governments.domain.party import Party


class GovernmentsReader(Protocol):
    def terms(self, territory_id: str | None = None) -> list[GovernmentTerm]:
        """Every stored term, or only those of one territory."""
        ...

    def parties(self) -> list[Party]: ...


class CompetencesReader(Protocol):
    """Read-only port for the competence table; a separate port, so a use case that needs only
    competences does not receive the terms too."""

    def competences(self) -> list[Competence]: ...


def government_on(reader: GovernmentsReader, territory_id: str, day: date) -> GovernmentTerm | None:
    """The term governing `territory_id` on `day`, or None if the dataset has none."""
    return in_force_on(reader.terms(territory_id), territory_id, day)
